#!/usr/bin/env python3
"""fleet-build — aggregate every goal-loop across ALL relevant branches into one
team dashboard (static JSON + HTML), built for GitHub Actions + GitHub Pages.

Loops don't only live on the default branch: a `pr-lane` loop works on feature
branches, and each branch carries its own `plans/loop/*.md` markers. This script
reads the markers straight out of git (no checkouts) for every branch with
recent activity, plus the signals hub from the working tree, and emits:

  <out>/data.json    machine-readable fleet state
  <out>/index.html   self-contained dashboard (no network fetches, dark/light,
                     ages computed client-side so a stale page is visibly stale)

The dashboard is also EDITABLE, with no server: paste a fine-grained GitHub PAT
(contents: read/write on this repo; stored only in your browser's localStorage)
and the Pause / Resume / Stop buttons commit a `status:` edit to the marker on
its branch via the GitHub Contents API. The loop honors upstream marker edits at
its next cycle (see loop.md "remote control"), so the buttons are real controls,
just asynchronous ones. Git stays the only data plane; there is no backend.

Usage:
  fleet-build.py --out _site [--root DIR] [--days N] [--repo owner/name]

  --out    output directory (required; created if missing)
  --root   repo to read (default .)
  --days   how far back a branch's last commit may be to count as relevant
           (default 14; the default branch is always included)
  --repo   owner/name for the edit-back API (default: $GITHUB_REPOSITORY,
           else parsed from `git remote get-url origin`)
"""
import glob
import html
import json
import os
import re
import subprocess
import sys
import time


def git(root, *args):
    try:
        r = subprocess.run(["git", "-C", root, *args], capture_output=True,
                           text=True, timeout=60)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def parse_frontmatter(text):
    m = re.search(r"^---\s*$(.*?)^---\s*$", text[:8000], re.S | re.M)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^\s*([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", line)
        if kv:
            fm[kv.group(1)] = kv.group(2)
    return fm if "status" in fm else None


def default_branch(root):
    head = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if head:
        return head.strip().split("/", 1)[-1]
    for name in ("main", "master"):
        if git(root, "rev-parse", "--verify", "--quiet", name) is not None:
            return name
    return "main"


def relevant_branches(root, days):
    """[(branch, last_commit_ts)] with activity in the window + the default branch.
    Prefers remote-tracking refs (CI fetches those); falls back to local heads."""
    out = git(root, "for-each-ref", "refs/remotes/origin",
              "--format=%(refname:short) %(committerdate:unix)")
    prefix = "origin/"
    if not out or not out.strip():
        out = git(root, "for-each-ref", "refs/heads",
                  "--format=%(refname:short) %(committerdate:unix)") or ""
        prefix = ""
    cutoff = time.time() - days * 86400
    default = default_branch(root)
    branches = {}
    for line in out.splitlines():
        parts = line.rsplit(" ", 1)
        if len(parts) != 2:
            continue
        ref, ts = parts[0], int(parts[1] or 0)
        name = ref[len(prefix):] if prefix and ref.startswith(prefix) else ref
        if name == "HEAD":
            continue
        if ts >= cutoff or name == default:
            branches[name] = (ref, ts)
    return sorted(branches.items(), key=lambda kv: -kv[1][1]), default


TASK_PATH = re.compile(r"^plans/loop/([^/]+)-tasks/[^/]+\.md$")


def branch_loops(root, name, ref):
    """Read plans/loop/*.md markers and plans/loop/<goal>-tasks/*.md task files
    from a branch without checking it out."""
    listing = git(root, "ls-tree", "-r", "--name-only", ref, "plans/loop/") or ""
    loops, tasks = [], []
    for path in listing.splitlines():
        if not path.endswith(".md"):
            continue
        task = TASK_PATH.match(path)
        if task is None and path.count("/") != 2:
            continue                      # nested non-task files: neither kind
        text = git(root, "show", f"{ref}:{path}")
        if not text:
            continue
        fm = parse_frontmatter(text)
        if not fm:
            continue
        ts = git(root, "log", "-1", "--format=%ct", ref, "--", path)
        fm["_branch"] = name
        fm["_path"] = path
        fm["_ts"] = int(ts.strip()) if ts and ts.strip() else 0
        if task:
            fm["_goal"] = task.group(1)
            tasks.append(fm)
        else:
            loops.append(fm)
    return loops, tasks


def read_signals(root):
    """Signal counts + recent list from the working tree (the checked-out default
    branch in CI). Signals are the committed team hub, so the worktree is right."""
    counts, recent = {}, []
    for path in sorted(glob.glob(os.path.join(root, "signals", "*.md")), reverse=True):
        base = os.path.basename(path)
        # same exclusions as signals-build.py: hub scaffolding is not a signal
        if base.upper() in ("INDEX.MD", "README.MD") or base.upper().startswith("INDEX"):
            continue
        try:
            fm = parse_frontmatter(open(path, encoding="utf-8").read(4000)) or {}
        except Exception:
            continue
        st = fm.get("status", "new")
        counts[st] = counts.get(st, 0) + 1
        if len(recent) < 8:
            recent.append({"file": base, "status": st,
                           "type": fm.get("type", ""), "author": fm.get("author", "")})
    return {"counts": counts, "recent": recent}


def detect_repo(root):
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    url = (git(root, "remote", "get-url", "origin") or "").strip()
    m = re.search(r"[:/]([^/:]+/[^/]+?)(\.git)?$", url)
    return m.group(1) if m else ""


KEEP = ("status", "goalId", "goal", "cycle", "maxCycles", "deliveryMode",
        "linearProject", "backlogOpen", "backlogInProgress", "backlogDone",
        "backlogBlocked", "lastOutcome", "runnerHeartbeatAt")
TKEEP = ("status", "title", "score", "owner", "pr", "linearId")
TORDER = {"in_progress": 0, "open": 1, "parked": 2, "done": 3}
TASK_CAP = 50            # per loop, in the emitted data (highest-scored kept)


def task_score(t):
    try:
        return float(t.get("score", 0))
    except (TypeError, ValueError):
        return 0.0


def build_data(root, days, repo):
    branches, default = relevant_branches(root, days)
    # A marker inherited from the fork point shows up on every descendant branch;
    # that's history, not N loops. Dedup by path, keeping the branch with the
    # newest last-touch commit (where the loop actually checkpoints); on a tie
    # prefer the default branch. Task files get the exact same treatment.
    best, tbest = {}, {}

    def keep_newest(store, row, ts_key):
        cur = store.get(row["path"])
        if (cur is None or row[ts_key] > cur[ts_key]
                or (row[ts_key] == cur[ts_key]
                    and row["branch"] == default != cur["branch"])):
            store[row["path"]] = row

    for name, (ref, _ts) in branches:
        markers, tfiles = branch_loops(root, name, ref)
        for fm in markers:
            row = {k: fm[k] for k in KEEP if k in fm}
            row.update(branch=fm["_branch"], path=fm["_path"],
                       checkpointTs=fm["_ts"])
            keep_newest(best, row, "checkpointTs")
        for fm in tfiles:
            row = {k: fm[k] for k in TKEEP if k in fm}
            row.update(branch=fm["_branch"], path=fm["_path"], ts=fm["_ts"],
                       goal=fm["_goal"], file=os.path.basename(fm["_path"]))
            keep_newest(tbest, row, "ts")

    tasks_by_goal = {}
    for row in tbest.values():
        tasks_by_goal.setdefault(row.pop("goal"), []).append(row)
    for rows in tasks_by_goal.values():
        rows.sort(key=lambda t: (TORDER.get(t.get("status", ""), 4),
                                 -task_score(t), t.get("title", "")))
        del rows[TASK_CAP:]

    loops = list(best.values())
    for row in loops:
        row["tasks"] = tasks_by_goal.get(os.path.basename(row["path"])[:-3], [])
    order = {"active": 0, "paused": 1, "done": 2}
    loops.sort(key=lambda r: (order.get(r.get("status", ""), 3), -r["checkpointTs"]))
    return {
        "generated": int(time.time()),
        "repo": repo,
        "defaultBranch": default,
        "windowDays": days,
        "branchesScanned": [n for n, _ in branches],
        "loops": loops,
        "signals": read_signals(root),
    }


PAGE = """<!doctype html>
<meta charset="utf-8">
<meta http-equiv="refresh" content="120">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Loobster fleet</title>
<style>
  :root {
    --bg: oklch(98% .003 250); --panel: oklch(95.5% .005 250); --card: oklch(100% 0 0);
    --line: oklch(88% .008 250); --line2: oklch(78% .012 250);
    --ink: oklch(25% .015 260); --muted: oklch(45% .015 260);
    --accent: oklch(53% .19 27);
    --ok: oklch(50% .13 150); --warn: oklch(52% .12 75); --info: oklch(48% .1 250);
    --focus: oklch(55% .15 250);
    --shadow: 0 1px 2px oklch(20% .02 260 / .06), 0 4px 12px oklch(20% .02 260 / .05);
  }
  @media (prefers-color-scheme: dark) { :root {
    --bg: oklch(17% .012 260); --panel: oklch(20.5% .012 260); --card: oklch(23% .012 260);
    --line: oklch(31% .012 260); --line2: oklch(40% .012 260);
    --ink: oklch(93% .005 260); --muted: oklch(71% .01 260);
    --accent: oklch(68% .17 25);
    --ok: oklch(76% .14 150); --warn: oklch(80% .12 80); --info: oklch(75% .1 250);
    --focus: oklch(75% .12 250);
    --shadow: 0 1px 2px oklch(0% 0 0 / .3), 0 4px 14px oklch(0% 0 0 / .22);
  }}
  * { box-sizing: border-box }
  html { background:var(--bg) }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
  :focus-visible { outline:2px solid var(--focus); outline-offset:2px }
  .top { position:sticky; top:0; z-index:10; display:flex; align-items:center; gap:14px;
         padding:10px 18px; background:var(--panel); border-bottom:1px solid var(--line);
         flex-wrap:wrap }
  .brand { font-size:15px; font-weight:700; white-space:nowrap }
  .brand em { font-style:normal; color:var(--accent) }
  .tabs { display:flex; gap:2px; background:var(--bg); border:1px solid var(--line);
          border-radius:8px; padding:2px }
  .tab { border:0; background:transparent; color:var(--muted); padding:4px 12px;
         border-radius:6px; font:inherit; font-size:12px; cursor:pointer;
         transition:color .15s, background .15s }
  .tab:hover { color:var(--ink) }
  .tab[aria-selected="true"] { background:var(--card); color:var(--ink); box-shadow:var(--shadow) }
  .tab .n { color:var(--muted); font-size:11px }
  .ctl { margin-left:auto; display:inline-flex; align-items:center; gap:7px; font:inherit;
         font-size:12px; color:var(--muted); background:transparent; border:1px solid var(--line);
         border-radius:999px; padding:4px 12px; cursor:pointer; transition:all .15s }
  .ctl:hover { color:var(--ink); border-color:var(--line2) }
  .dot { width:8px; height:8px; border-radius:50%; background:var(--line2); flex:none }
  .dot.on { background:var(--ok) }
  .sub { color:var(--muted); font-size:12px; padding:10px 18px 0 }
  main { padding:14px 18px 48px; max-width:1280px; margin:0 auto }
  .toolbar { display:flex; flex-wrap:wrap; gap:8px 10px; align-items:center; margin:2px 0 14px }
  .chips { display:flex; flex-wrap:wrap; gap:6px }
  .chip { font:inherit; font-size:12px; color:var(--muted); background:transparent;
          border:1px solid var(--line); border-radius:999px; padding:3px 11px; cursor:pointer;
          display:inline-flex; align-items:center; gap:6px; transition:all .15s }
  .chip:hover { color:var(--ink); border-color:var(--line2) }
  .chip[aria-pressed="true"] { color:var(--ink); border-color:var(--ink) }
  .chip .dot { width:7px; height:7px }
  .addform { display:flex; gap:6px; margin-left:auto; flex-wrap:wrap }
  select, input { font:inherit; font-size:12px; color:var(--ink); background:var(--card);
          border:1px solid var(--line); border-radius:7px; padding:5px 9px }
  input::placeholder { color:var(--muted) }
  .btn { font:inherit; font-size:12px; color:var(--ink); background:var(--card);
         border:1px solid var(--line); border-radius:7px; padding:5px 11px; cursor:pointer;
         transition:border-color .15s, background .15s }
  .btn:hover { border-color:var(--line2) }
  .btn:active { transform:translateY(.5px) }
  .btn.primary { color:var(--accent);
         border-color:color-mix(in oklch, var(--accent) 45%, var(--line)) }
  .btn.primary:hover { border-color:var(--accent) }
  .board { display:grid; grid-template-columns:repeat(4, minmax(240px, 1fr)); gap:10px;
           overflow-x:auto; scroll-snap-type:x proximity; padding-bottom:6px }
  .col { min-width:240px; scroll-snap-align:start }
  .colh { font-size:11px; font-weight:700; letter-spacing:.02em; text-transform:uppercase;
          color:var(--muted); padding:0 2px 8px; display:flex; gap:7px; align-items:center }
  .colh .dot { width:7px; height:7px }
  .colh .cnt { font-weight:400 }
  .list { display:flex; flex-direction:column; gap:8px; min-height:24px }
  .tcard { background:var(--card); border:1px solid var(--line); border-radius:9px;
           padding:9px 11px; box-shadow:var(--shadow); transition:border-color .15s }
  .tcard:hover { border-color:var(--line2) }
  .tmeta { display:flex; flex-wrap:wrap; gap:5px 10px; align-items:center; margin-top:7px;
           font-size:11px; color:var(--muted) }
  .loopchip { display:inline-flex; align-items:center; gap:5px; border:1px solid var(--line);
              border-radius:999px; padding:1px 8px }
  .loopchip .dot { width:7px; height:7px }
  .tact { display:flex; gap:5px; margin-top:8px }
  .tbtn { font:inherit; font-size:11px; padding:2px 9px; border-radius:6px;
          border:1px solid var(--line); background:transparent; color:var(--muted);
          cursor:pointer; transition:all .15s }
  .tbtn:hover { color:var(--ink); border-color:var(--line2) }
  @keyframes moved { from { box-shadow:0 0 0 3px color-mix(in oklch, var(--info) 40%, transparent) }
                     to { box-shadow:var(--shadow) } }
  .moved { animation:moved .5s ease-out }
  .loops { display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:12px }
  .lcard { background:var(--card); border:1px solid var(--line); border-radius:10px;
           padding:14px 16px; box-shadow:var(--shadow) }
  .lhead { display:flex; flex-wrap:wrap; gap:6px 12px; align-items:center }
  .pill { display:inline-flex; align-items:center; gap:6px; font-size:11px; font-weight:600;
          border:1px solid var(--line); border-radius:999px; padding:2px 10px }
  .pill .dot { width:7px; height:7px }
  .pill.active { color:var(--ok) }  .pill.active .dot { background:var(--ok) }
  .pill.paused { color:var(--warn) } .pill.paused .dot { background:var(--warn) }
  .pill.done { color:var(--muted) }  .pill.done .dot { background:var(--muted) }
  .goal { font-size:15px; font-weight:600; margin:8px 0 2px; text-wrap:balance }
  .kv { color:var(--muted); font-size:12px } .kv b { color:var(--ink); font-weight:600 }
  .meta { display:flex; flex-wrap:wrap; gap:3px 14px; margin-top:6px }
  .bar { height:4px; border-radius:2px; background:var(--line); overflow:hidden; margin-top:10px }
  .bar i { display:block; height:100%; background:var(--ok); transition:width .3s }
  .age { color:var(--muted); font-size:11px; margin-top:10px }
  .lact { display:flex; gap:6px; align-items:center; margin-top:10px; flex-wrap:wrap }
  .empty { border:1px dashed var(--line2); border-radius:10px; padding:20px 22px;
           color:var(--muted); max-width:560px; line-height:1.7 }
  .empty b { color:var(--ink) }
  .sigrow { display:flex; gap:6px 14px; padding:7px 2px; border-bottom:1px solid var(--line);
            font-size:12px; flex-wrap:wrap; align-items:baseline }
  code { background:var(--panel); border:1px solid var(--line); border-radius:4px; padding:0 5px }
  a { color:var(--info) }
  dialog { background:var(--card); color:var(--ink); border:1px solid var(--line);
           border-radius:12px; padding:20px 22px; max-width:520px; font:inherit;
           box-shadow:var(--shadow) }
  dialog::backdrop { background:oklch(10% .01 260 / .45) }
  dialog h2 { font-size:14px; margin:0 0 6px }
  dialog p { font-size:12px; line-height:1.65; color:var(--muted); margin:8px 0 }
  dialog b { color:var(--ink) }
  dialog .row { display:flex; gap:6px; margin-top:12px; flex-wrap:wrap }
  dialog input { flex:1 1 200px }
  .toast { position:fixed; left:50%; bottom:18px; transform:translateX(-50%);
           background:var(--card); border:1px solid var(--line); border-radius:9px;
           box-shadow:var(--shadow); color:var(--ink); font-size:12px; padding:8px 14px;
           opacity:0; pointer-events:none; transition:opacity .2s; z-index:30; max-width:90vw }
  .toast.show { opacity:1 }
  @media (max-width:720px) {
    .top { padding:10px 12px } .sub { padding:10px 12px 0 }
    main { padding:12px 12px 48px }
    .addform { margin-left:0; width:100% }
    .addform input:not([type=hidden]) { flex:1 }
  }
  @media (prefers-reduced-motion: reduce) {
    * { transition:none !important; animation:none !important }
  }
</style>
<header class="top">
  <div class="brand">&#129438; Loobster <em>fleet</em></div>
  <nav class="tabs" aria-label="Views">
    <button class="tab" id="tab-board" aria-selected="false" onclick="go('board')">Board <span class="n" id="n-board"></span></button>
    <button class="tab" id="tab-loops" aria-selected="false" onclick="go('loops')">Loops <span class="n" id="n-loops"></span></button>
    <button class="tab" id="tab-signals" aria-selected="false" onclick="go('signals')">Signals <span class="n" id="n-signals"></span></button>
  </nav>
  <button class="ctl" onclick="document.getElementById('tokendlg').showModal()">
    <span class="dot" id="tokendot"></span><span id="tokenlabel">controls off</span></button>
</header>
<div class="sub" id="sub"></div>
<main>
  <section id="view-board" hidden>
    <div class="toolbar" id="toolbar"></div>
    <div class="board" id="kanban"></div>
  </section>
  <section id="view-loops" hidden><div class="loops" id="fleet"></div></section>
  <section id="view-signals" hidden><div id="signals"></div></section>
</main>
<dialog id="tokendlg">
  <h2>Dashboard controls</h2>
  <p>Every control here is a git commit made via the GitHub API: pause / resume / stop edits a
  loop's marker <code>status:</code>, a board move edits that task's file, and &ldquo;Add
  task&rdquo; creates one &mdash; each on the loop's own branch. Loops adopt upstream edits at
  their next cycle, so actions apply asynchronously, and every one is audit-logged.</p>
  <p><a href="https://github.com/settings/personal-access-tokens/new" target="_blank"
  rel="noopener">Create a fine-grained PAT &#8599;</a> &mdash; Repository access &rarr;
  <b>Only select repositories</b> &rarr; <b class="repname"></b> &middot; Permissions &rarr;
  <b>Contents: Read and write</b>. (GitHub has no API for creating PATs, so those two clicks
  stay manual by design.)</p>
  <p>The token is stored only in this browser (localStorage) and sent only to api.github.com.</p>
  <form method="dialog" class="row">
    <input id="pat" type="password" placeholder="github_pat_..." autocomplete="off">
    <button class="btn primary" onclick="savePat()">Save</button>
    <button class="btn" onclick="clearPat()">Clear</button>
    <button class="btn">Close</button>
  </form>
</dialog>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script id="fleet-data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('fleet-data').textContent);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const age = ts => { if (!ts) return '?';
  const s = Math.max(0, Date.now()/1000 - ts);
  return s < 90 ? Math.round(s)+'s' : s < 5400 ? Math.round(s/60)+'m' : (s/3600).toFixed(1)+'h'; };
const KEY = 'loobster-fleet-pat';
const HUES = [150, 250, 27, 75, 200, 320];
const loopHue = id => HUES[[...String(id)].reduce((a, c) => a + c.charCodeAt(0), 0) % HUES.length];
const dotCss = id => `oklch(60% .14 ${loopHue(id)})`;
let filter = null;

const COLS = [['in_progress','In progress','var(--info)'], ['open','Open','var(--line2)'],
              ['parked','Parked','var(--warn)'], ['done','Done','var(--ok)']];
const MOVES = { open: [['start','in_progress'],['done','done'],['park','parked']],
                in_progress: [['done','done'],['park','parked']],
                parked: [['reopen','open']], done: [] };

const allTasks = () => DATA.loops.flatMap((l, li) => (l.tasks || []).map((t, ti) => ({t, l, li, ti})));
const chip = l => `<span class="loopchip"><span class="dot" style="background:${dotCss(l.goalId)}"></span>${esc(l.goalId)}</span>`;
const emptyLoops = () => `<div class="empty" style="grid-column:1/-1"><b>No goal-loops on any
  recent branch.</b><br>Start one with <code>/loobster:loop &lt;goal&gt;</code> &mdash; its
  backlog, status, and controls appear here.</div>`;

document.getElementById('sub').textContent =
  `${DATA.repo} · generated ${age(DATA.generated)} ago · ` +
  `${DATA.branchesScanned.length} branches scanned (last ${DATA.windowDays}d) · page refreshes every 2min`;
for (const el of document.querySelectorAll('.repname')) el.textContent = DATA.repo;

function toast(msg){
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toast._h); toast._h = setTimeout(() => t.classList.remove('show'), 2800);
}
function refreshToken(){
  const on = !!localStorage.getItem(KEY);
  document.getElementById('tokendot').classList.toggle('on', on);
  document.getElementById('tokenlabel').textContent = on ? 'controls on' : 'controls off';
}
function savePat(){
  const v = document.getElementById('pat').value.trim();
  if (v) { localStorage.setItem(KEY, v); toast('token saved (this browser only)'); }
  refreshToken();
}
function clearPat(){
  localStorage.removeItem(KEY); document.getElementById('pat').value = '';
  toast('token cleared'); refreshToken();
}
function needToken(){
  if (localStorage.getItem(KEY)) return false;
  document.getElementById('tokendlg').showModal();
  toast('save a token to enable controls'); return true;
}

function go(view){
  for (const v of ['board','loops','signals']) {
    document.getElementById('view-' + v).hidden = v !== view;
    document.getElementById('tab-' + v).setAttribute('aria-selected', v === view);
  }
  if (location.hash !== '#' + view) history.replaceState(null, '', '#' + view);
}
function setFilter(goalId){ filter = goalId; renderBoard(); }

function renderCounts(){
  document.getElementById('n-board').textContent = allTasks().length || '';
  document.getElementById('n-loops').textContent = DATA.loops.length || '';
  const sig = DATA.signals || {counts:{}};
  const n = Object.values(sig.counts).reduce((a, b) => a + b, 0);
  document.getElementById('n-signals').textContent = n || '';
}

function tcard(r, st){
  const {t, l, li, ti} = r;
  return `<div class="tcard" id="tc-${li}-${ti}">
    <div>${esc(t.title || t.file)}</div>
    <div class="tmeta">${chip(l)}<span title="RICE score">rice ${esc(t.score ?? '?')}</span>
      ${t.owner ? `<span>${esc(t.owner)}</span>` : ''}
      ${t.pr ? `<a href="${esc(t.pr)}" target="_blank" rel="noopener">PR</a>` : ''}</div>
    ${MOVES[st].length ? `<div class="tact">${MOVES[st].map(([lbl, next]) =>
      `<button class="tbtn" onclick="setTaskStatus(${li},${ti},'${next}')">${lbl}</button>`).join('')}</div>` : ''}
  </div>`;
}

function renderBoard(){
  const rows = allTasks().filter(r => !filter || r.l.goalId === filter);
  const ctl = DATA.loops.filter(l => l.status === 'active' || l.status === 'paused');
  const chips = DATA.loops.length > 1 ? `<div class="chips">` +
    [`<button class="chip" aria-pressed="${!filter}" onclick="setFilter(null)">all loops</button>`,
     ...DATA.loops.map(l => `<button class="chip" aria-pressed="${filter === l.goalId}"
        onclick="setFilter('${esc(l.goalId)}')"><span class="dot"
        style="background:${dotCss(l.goalId)}"></span>${esc(l.goalId)}</button>`)].join('') + `</div>` : '';
  const form = ctl.length ? `<form class="addform" onsubmit="addTask(event)">
      ${ctl.length > 1
        ? `<select id="nt-loop" aria-label="loop">${ctl.map(l =>
             `<option value="${esc(l.goalId)}">${esc(l.goalId)}</option>`).join('')}</select>`
        : `<input type="hidden" id="nt-loop" value="${esc(ctl[0].goalId)}">`}
      <input id="nt-title" placeholder="file a task for the loop…" size="26" aria-label="task title">
      <button class="btn primary">Add task</button></form>` : '';
  document.getElementById('toolbar').innerHTML = chips + form;
  const board = document.getElementById('kanban');
  if (!DATA.loops.length) { board.innerHTML = emptyLoops(); return; }
  if (!rows.length) {
    board.innerHTML = `<div class="empty" style="grid-column:1/-1"><b>No tasks on the
      board${filter ? ` for ${esc(filter)}` : ''}.</b><br>Tasks appear when a loop checkpoints
      its backlog to <code>plans/loop/&lt;goal&gt;-tasks/</code> &mdash; or file one with
      &ldquo;Add task&rdquo; and the loop adopts it next cycle.</div>`;
    return;
  }
  board.innerHTML = COLS.map(([st, label, color]) => {
    const items = rows.filter(r => (r.t.status || 'open') === st);
    return `<div class="col"><div class="colh"><span class="dot" style="background:${color}"></span>
      ${label} <span class="cnt">${items.length}</span></div>
      <div class="list">${items.map(r => tcard(r, st)).join('')}</div></div>`;
  }).join('');
}

function renderLoops(){
  const el = document.getElementById('fleet');
  if (!DATA.loops.length) { el.innerHTML = emptyLoops(); return; }
  el.innerHTML = DATA.loops.map((l, i) => {
    const cyc = l.maxCycles ? `${esc(l.cycle ?? '?')} / ${esc(l.maxCycles)}` : esc(l.cycle ?? '?');
    const counts = ['backlogOpen','backlogInProgress','backlogDone'].map(k => parseInt(l[k], 10) || 0);
    const total = Math.max(1, counts[0] + counts[1] + counts[2]);
    const parked = parseInt(l.backlogBlocked, 10) || 0;
    const extras = [l.deliveryMode && `delivery <b>${esc(l.deliveryMode)}</b>`,
                    l.linearProject && `linear <b>${esc(l.linearProject)}</b>`].filter(Boolean);
    const canCtl = l.status === 'active' || l.status === 'paused';
    const ntasks = (l.tasks || []).length;
    return `<div class="lcard">
      <div class="lhead">
        <span class="pill ${esc(l.status)}"><span class="dot"></span>${esc(l.status)}</span>
        ${chip(l)}
        <span class="kv">branch <b>${esc(l.branch)}</b></span>
        <span class="kv">cycle <b>${cyc}</b></span>
      </div>
      <div class="goal">${esc(l.goal ?? l.goalId ?? l.path)}</div>
      ${(l.backlogOpen ?? l.backlogDone) !== undefined ? `
        <div class="kv">backlog: <b>${counts[0]}</b> open &middot; <b>${counts[1]}</b> in progress
          &middot; <b>${counts[2]}</b> done${parked ? ` &middot; <b>${parked}</b> parked` : ''}</div>
        <div class="bar"><i style="width:${Math.round(100 * counts[2] / total)}%"></i></div>` : ''}
      ${extras.length ? `<div class="meta">${extras.map(x => `<span class="kv">${x}</span>`).join('')}</div>` : ''}
      ${l.lastOutcome ? `<div class="kv" style="margin-top:6px">last: <b>${esc(l.lastOutcome)}</b></div>` : ''}
      <div class="age">checkpointed ${age(l.checkpointTs)} ago &middot; ${esc(l.path)}</div>
      <div class="lact">
        ${canCtl ? (l.status === 'active'
          ? `<button class="btn" onclick="setStatus(${i},'paused')">Pause</button>`
          : `<button class="btn" onclick="setStatus(${i},'active')">Resume</button>`) +
          `<button class="btn" onclick="setStatus(${i},'done')">Stop</button>` : ''}
        ${ntasks ? `<button class="btn" onclick="setFilter('${esc(l.goalId)}');go('board')">
           Board (${ntasks})</button>` : ''}
      </div>
    </div>`;
  }).join('');
}

function renderSignals(){
  const sig = DATA.signals || {counts:{}, recent:[]};
  const counts = Object.entries(sig.counts).map(([k, v]) => `<b>${v}</b> ${esc(k)}`).join(' &middot; ');
  document.getElementById('signals').innerHTML =
    `<div class="kv" style="margin-bottom:8px">${counts || ''}</div>` +
    (sig.recent.length ? sig.recent.map(s =>
      `<div class="sigrow"><span>${esc(s.file)}</span><b>${esc(s.status)}</b>
       <span class="kv">${esc(s.type)}</span><span class="kv">${esc(s.author)}</span></div>`).join('')
     : `<div class="empty"><b>No signals yet.</b><br>Emit one with <code>/signals</code> &mdash;
        observations land here for every loop and teammate to consume.</div>`);
}

function ghHeaders(){
  const pat = localStorage.getItem(KEY);
  if (!pat) throw new Error('no token');
  return { Authorization: `Bearer ${pat}`, Accept: 'application/vnd.github+json' };
}
function b64(text){
  const bytes = new TextEncoder().encode(text);
  let bin = ''; bytes.forEach(b => bin += String.fromCharCode(b));
  return btoa(bin);
}
async function editStatusFile(path, branch, status, message){
  const api = `https://api.github.com/repos/${DATA.repo}/contents/${path}`;
  const headers = ghHeaders();
  const cur = await (await fetch(`${api}?ref=${encodeURIComponent(branch)}`, { headers })).json();
  if (!cur.sha) throw new Error(cur.message || 'fetch failed');
  const text = new TextDecoder().decode(Uint8Array.from(atob(cur.content.replace(/\\n/g,'')), c => c.charCodeAt(0)));
  const next = text.replace(/^(\\s*status\\s*:\\s*)\\S+/m, `$1${status}`);
  if (next === text) throw new Error('no status line found');
  const put = await (await fetch(api, { method: 'PUT', headers, body: JSON.stringify({
    message, content: b64(next), sha: cur.sha, branch }) })).json();
  if (!put.commit) throw new Error(put.message || 'commit failed');
}

async function setStatus(i, status){
  const l = DATA.loops[i];
  if (needToken()) return;
  if (status === 'done' && !confirm(`Stop loop "${l.goalId}" on ${l.branch}?`)) return;
  try {
    await editStatusFile(l.path, l.branch, status,
      `fleet-dashboard: ${l.goalId} status -> ${status}`);
    toast(`committed to ${l.branch} — the loop adopts it next cycle`);
  } catch (e) { toast('error: ' + e.message); }
}

async function setTaskStatus(li, ti, status){
  const l = DATA.loops[li], t = l.tasks[ti];
  if (needToken()) return;
  try {
    await editStatusFile(t.path, t.branch, status,
      `fleet-dashboard: task "${t.title || t.file}" -> ${status}`);
    t.status = status;
    renderBoard(); renderCounts();
    const el = document.getElementById(`tc-${li}-${ti}`);
    if (el) el.classList.add('moved');
    toast(`committed to ${t.branch} — the loop adopts it next cycle`);
  } catch (e) { toast('error: ' + e.message); }
}

async function addTask(ev){
  ev.preventDefault();
  const goalId = document.getElementById('nt-loop').value;
  const li = DATA.loops.findIndex(l => l.goalId === goalId);
  const l = DATA.loops[li];
  const title = (document.getElementById('nt-title').value || '').trim();
  if (!title) { toast('enter a task title'); return; }
  if (needToken()) return;
  try {
    const headers = ghHeaders();
    const goal = l.path.replace(/^plans\\/loop\\//, '').replace(/\\.md$/, '');
    const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '').slice(0, 40) || 'task';
    const path = `plans/loop/${goal}-tasks/${Date.now()}-${slug}.md`;
    const body = `---\\nstatus: open\\ntitle: ${title.replace(/\\s+/g, ' ')}\\n` +
      `score: 0\\nowner: board\\n---\\nfiled from the fleet dashboard\\n`;
    const put = await (await fetch(`https://api.github.com/repos/${DATA.repo}/contents/${path}`, {
      method: 'PUT', headers, body: JSON.stringify({
        message: `fleet-dashboard: add task "${title}"`,
        content: b64(body), branch: l.branch }) })).json();
    if (!put.commit) throw new Error(put.message || 'commit failed');
    (l.tasks = l.tasks || []).push({ title, status: 'open', score: '0', owner: 'board',
      path, branch: l.branch, file: path.split('/').pop() });
    document.getElementById('nt-title').value = '';
    renderBoard(); renderCounts();
    toast(`task committed to ${l.branch} — the loop adopts + scores it next cycle`);
  } catch (e) { toast('error: ' + e.message); }
}

renderCounts(); renderBoard(); renderLoops(); renderSignals(); refreshToken();
const start = ['board','loops','signals'].includes(location.hash.slice(1))
  ? location.hash.slice(1) : (allTasks().length ? 'board' : 'loops');
go(start);
requestAnimationFrame(() => {   // fragment/scroller focus artifact on load
  if (document.activeElement && document.activeElement !== document.body)
    document.activeElement.blur();
  window.scrollTo(0, 0);
});
window.addEventListener('hashchange', () => {
  const v = location.hash.slice(1);
  if (['board','loops','signals'].includes(v)) go(v);
});
</script>
"""


def main(argv):
    root, out, days, repo = ".", None, 14, None
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == "--out" and args:
            out = args.pop(0)
        elif a == "--root" and args:
            root = args.pop(0)
        elif a == "--days" and args:
            try:
                days = int(args.pop(0))
            except ValueError:
                print("error: --days needs an integer"); return 2
        elif a == "--repo" and args:
            repo = args.pop(0)
        elif a in ("-h", "--help"):
            print(__doc__.strip()); return 0
        else:
            print(f"error: unknown argument '{a}' (see --help)"); return 2
    if not out:
        print("error: --out is required (e.g. --out _site)"); return 2
    if git(root, "rev-parse", "--git-dir") is None:
        print(f"error: {root} is not a git repository"); return 2
    data = build_data(root, days, repo or detect_repo(root))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    payload = json.dumps(data).replace("</", "<\\/")
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(PAGE.replace("__DATA__", payload))
    print(f"fleet: {len(data['loops'])} loop(s) across {len(data['branchesScanned'])} "
          f"branch(es) -> {out}/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
