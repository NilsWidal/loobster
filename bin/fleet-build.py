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
<title>Loobster fleet</title>
<style>
  :root { --bg:#fff; --fg:#1f2328; --muted:#59636e; --card:#f6f8fa; --line:#d1d9e0;
          --active:#1a7f37; --paused:#9a6700; --done:#59636e; --alert:#cf222e; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0d1117; --fg:#f0f6fc; --muted:#9198a1; --card:#151b23; --line:#3d444d;
            --active:#3fb950; --paused:#d29922; --done:#9198a1; --alert:#f85149; } }
  body { margin:0; padding:24px; background:var(--bg); color:var(--fg);
         font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; }
  h1 { font-size:16px; margin:0 0 4px; } h1 span { color:var(--alert); }
  .sub { color:var(--muted); margin-bottom:16px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:8px;
          padding:14px 16px; margin-bottom:14px; max-width:900px; }
  .row { display:flex; flex-wrap:wrap; gap:8px 16px; align-items:baseline; }
  .pill { padding:1px 10px; border-radius:999px; font-weight:600; font-size:12px;
          border:1px solid currentColor; }
  .active { color:var(--active); } .paused { color:var(--paused); }
  .done { color:var(--done); } .alert { color:var(--alert); }
  .goal { font-weight:600; margin:6px 0 2px; }
  .kv { color:var(--muted); } .kv b { color:var(--fg); font-weight:600; }
  .bar { height:6px; border-radius:3px; background:var(--line); overflow:hidden;
         margin-top:8px; max-width:420px; }
  .bar i { display:block; height:100%; background:var(--active); }
  .age { color:var(--muted); font-size:12px; margin-top:6px; }
  button { font:inherit; font-size:12px; padding:2px 10px; border-radius:6px;
           border:1px solid var(--line); background:var(--bg); color:var(--fg);
           cursor:pointer; } button:hover { border-color:var(--fg); }
  input { font:inherit; font-size:12px; padding:3px 8px; border-radius:6px;
          border:1px solid var(--line); background:var(--bg); color:var(--fg);
          width:280px; }
  .controls { margin-top:8px; display:flex; gap:8px; align-items:center; }
  .msg { font-size:12px; }
  .kb { display:flex; gap:8px; margin-top:10px; flex-wrap:wrap; }
  .col { flex:1 1 160px; min-width:150px; background:var(--bg);
         border:1px solid var(--line); border-radius:6px; padding:8px; }
  .col h4 { margin:0 0 6px; font-size:11px; color:var(--muted);
            text-transform:uppercase; letter-spacing:.04em; }
  .task { border:1px solid var(--line); border-radius:6px; padding:6px 8px;
          margin-bottom:6px; font-size:12px; }
  .task .row { gap:4px 8px; margin-top:4px; }
  .score { color:var(--muted); }
  .tbtn { font-size:11px; padding:0 7px; }
  details { margin:10px 0 18px; color:var(--muted); }
  code { background:var(--card); padding:1px 5px; border-radius:4px; }
</style>
<h1>&#129438; Loobster <span>fleet</span></h1>
<div class="sub" id="sub"></div>
<details>
  <summary>Enable dashboard controls (pause / resume / stop a loop)</summary>
  <p>Controls commit a <code>status:</code> edit to the loop's marker on its branch via the
  GitHub API. The loop adopts upstream marker edits at its next cycle, so a change here
  takes effect asynchronously. Paste a fine-grained PAT with <b>contents: read&amp;write</b>
  on this repo; it is stored only in this browser (localStorage), never sent anywhere
  except api.github.com.</p>
  <p><a href="https://github.com/settings/personal-access-tokens/new" target="_blank"
  rel="noopener">Create a fine-grained PAT &#8599;</a> &mdash; set Repository access &rarr;
  <b>Only select repositories</b> &rarr; <b id="repname"></b>, Permissions &rarr;
  <b>Contents: Read and write</b>, then paste it below. (GitHub has no API to create
  PATs, so those two clicks stay manual by design.)</p>
  <input id="pat" type="password" placeholder="github_pat_...">
  <button onclick="savePat()">Save token</button> <span class="msg" id="patmsg"></span>
</details>
<div id="fleet"></div>
<div class="card" id="signals"></div>
<script id="fleet-data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('fleet-data').textContent);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const age = ts => { if (!ts) return '?';
  const s = Math.max(0, Date.now()/1000 - ts);
  return s < 90 ? Math.round(s)+'s' : s < 5400 ? Math.round(s/60)+'m' : (s/3600).toFixed(1)+'h'; };
const KEY = 'loobster-fleet-pat';
function savePat(){ localStorage.setItem(KEY, document.getElementById('pat').value.trim());
  document.getElementById('patmsg').textContent = 'saved (this browser only)'; }

document.getElementById('sub').textContent =
  `${DATA.repo} · generated ${age(DATA.generated)} ago · ` +
  `${DATA.branchesScanned.length} branches scanned (last ${DATA.windowDays}d) · page refreshes every 2min`;
document.getElementById('repname').textContent = DATA.repo;

const TCOLS = [['in_progress','in progress'],['open','open'],['parked','parked'],['done','done']];
const TBTNS = { open: [['start','in_progress'],['done','done'],['park','parked']],
                in_progress: [['done','done'],['park','parked']],
                parked: [['reopen','open']], done: [] };

function kanban(l, i){
  if (!(l.tasks || []).length) return '';
  return `<div class="kb">` + TCOLS.map(([st, label]) => {
    const items = l.tasks.map((t, ti) => [t, ti]).filter(([t]) => (t.status || 'open') === st);
    return `<div class="col"><h4>${esc(label)} (${items.length})</h4>` + items.map(([t, ti]) =>
      `<div class="task"><div>${esc(t.title || t.file)}</div>
        <div class="row"><span class="score">rice ${esc(t.score ?? '?')}</span>
        ${t.pr ? `<a href="${esc(t.pr)}" target="_blank" rel="noopener">PR</a>` : ''}
        ${(TBTNS[st] || []).map(([lbl, next]) =>
          `<button class="tbtn" onclick="setTaskStatus(${i},${ti},'${next}')">${lbl}</button>`).join('')}
        <span class="msg" id="tmsg-${i}-${ti}"></span></div></div>`).join('') + `</div>`;
  }).join('') + `</div>`;
}

function card(l, i){
  const cyc = l.maxCycles ? `${esc(l.cycle ?? '?')} / ${esc(l.maxCycles)}` : esc(l.cycle ?? '?');
  const counts = ['backlogOpen','backlogInProgress','backlogDone'].map(k => parseInt(l[k],10) || 0);
  const total = Math.max(1, counts[0]+counts[1]+counts[2]);
  const parked = parseInt(l.backlogBlocked,10) || 0;
  const extras = [l.deliveryMode && `delivery <b>${esc(l.deliveryMode)}</b>`,
                  l.linearProject && `linear <b>${esc(l.linearProject)}</b>`].filter(Boolean);
  const canCtl = l.status === 'active' || l.status === 'paused';
  return `<div class="card">
    <div class="row">
      <span class="pill ${esc(l.status)}">${esc(l.status)}</span>
      <span class="kv">goalId <b>${esc(l.goalId ?? l.path)}</b></span>
      <span class="kv">branch <b>${esc(l.branch)}</b></span>
      <span class="kv">cycle <b>${cyc}</b></span>
    </div>
    <div class="goal">${esc(l.goal ?? '')}</div>
    ${(l.backlogOpen ?? l.backlogDone) !== undefined ? `
      <div class="kv">backlog: <b>${counts[0]}</b> open &middot; <b>${counts[1]}</b> in progress
        &middot; <b>${counts[2]}</b> done${parked ? ` &middot; <b class="paused">${parked}</b> parked` : ''}</div>
      <div class="bar"><i style="width:${Math.round(100*counts[2]/total)}%"></i></div>` : ''}
    ${extras.length ? `<div class="kv">${extras.join(' &middot; ')}</div>` : ''}
    ${l.lastOutcome ? `<div class="kv">last: <b>${esc(l.lastOutcome)}</b></div>` : ''}
    ${kanban(l, i)}
    <div class="age">checkpointed ${age(l.checkpointTs)} ago &middot; ${esc(l.path)}</div>
    ${canCtl ? `<div class="controls">
      ${l.status === 'active' ? `<button onclick="setStatus(${i},'paused')">Pause</button>` :
                                `<button onclick="setStatus(${i},'active')">Resume</button>`}
      <button onclick="setStatus(${i},'done')">Stop</button>
      <span class="msg" id="msg-${i}"></span></div>
    <div class="controls"><input id="nt-${i}" placeholder="new task title" style="width:220px">
      <button onclick="addTask(${i})">Add task</button>
      <span class="msg" id="ntmsg-${i}"></span></div>` : ''}
  </div>`;
}

function renderFleet(){
  document.getElementById('fleet').innerHTML = DATA.loops.length
    ? DATA.loops.map(card).join('')
    : '<div class="card"><div class="goal">No goal-loops on any recent branch.</div>' +
      '<div class="kv">Start one with /loobster:loop &lt;goal&gt;</div></div>';
}
renderFleet();

const sig = DATA.signals || {counts:{}, recent:[]};
document.getElementById('signals').innerHTML =
  `<div class="goal">Signals hub</div>
   <div class="kv">${Object.entries(sig.counts).map(([k,v]) => `<b>${v}</b> ${esc(k)}`).join(' &middot; ') || 'no signals'}</div>` +
  sig.recent.map(s => `<div class="kv">${esc(s.file)} <b>${esc(s.status)}</b> ${esc(s.type)} ${esc(s.author)}</div>`).join('');

function ghHeaders(){
  const pat = localStorage.getItem(KEY);
  if (!pat) throw new Error('save a token above first');
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
  const l = DATA.loops[i], msg = document.getElementById('msg-' + i);
  if (status === 'done' && !confirm(`Stop loop "${l.goalId}" on ${l.branch}?`)) return;
  msg.textContent = '...';
  try {
    await editStatusFile(l.path, l.branch, status,
      `fleet-dashboard: ${l.goalId} status -> ${status}`);
    msg.textContent = `committed; the loop adopts it next cycle`;
  } catch (e) { msg.textContent = 'error: ' + e.message; }
}

async function setTaskStatus(i, ti, status){
  const l = DATA.loops[i], t = l.tasks[ti];
  const msg = document.getElementById(`tmsg-${i}-${ti}`);
  msg.textContent = '...';
  try {
    await editStatusFile(t.path, t.branch, status,
      `fleet-dashboard: task "${t.title || t.file}" -> ${status}`);
    t.status = status;            // optimistic: the card moves column now,
    renderFleet();                // the loop adopts the commit next cycle
  } catch (e) { msg.textContent = 'error: ' + e.message; }
}

async function addTask(i){
  const l = DATA.loops[i];
  const inp = document.getElementById('nt-' + i), msg = document.getElementById('ntmsg-' + i);
  const title = (inp.value || '').trim();
  if (!title) { msg.textContent = 'enter a title'; return; }
  msg.textContent = '...';
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
    renderFleet();                // the loop adopts + re-scores it next cycle
  } catch (e) { msg.textContent = 'error: ' + e.message; }
}
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
