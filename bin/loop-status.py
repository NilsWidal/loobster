#!/usr/bin/env python3
"""loop-status — cross-tool status for Loobster goal-loops (terminal + HTML).

Reads the durable loop state that EVERY runtime writes — `plans/loop/*.md` marker
frontmatter and the `*.md.lock` runner leases — and renders it two ways:

  loop-status.py [--root DIR]          # terse terminal status (all loops)
  loop-status.py build [--root DIR]    # also (re)write plans/loop/status.html

The HTML is a single self-contained file (no network, no deps, auto-refreshes every
30s) that any browser can keep open as a live team/status board. Because it is
generated purely from files, it works identically whether the loop is being driven
by Claude Code, Codex, Cursor, or the external driver (bin/loobster-drive.sh) —
there is no agent API in the data path. The loop regenerates it at every cycle
checkpoint; `status.html` is safe to gitignore or commit (non-PHI only, like
signals — the marker's goal/outcome lines are team-visible text).

Frontmatter keys used (all optional except status/goalId): status, goalId, goal,
cycle, maxCycles, runner, runnerHeartbeatAt, reentry, backlogOpen,
backlogInProgress, backlogDone, backlogBlocked, lastOutcome, deliveryMode,
linearProject.
"""
import glob
import html
import os
import re
import sys
import time

LEASE_TTL = 3600  # mirror bin/loop-lease.py DEFAULT_TTL


def _loops_root(start):
    """Nearest ancestor of `start` (inclusive, bounded) that has a plans/loop dir.

    Same anchoring as bin/loop-rearm.py: a session cwd'd in a subdirectory must
    still find the project's markers, or the board silently goes stale."""
    p = os.path.abspath(start)
    for _ in range(10):
        if os.path.isdir(os.path.join(p, "plans", "loop")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return start


def _to_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_marker(path):
    try:
        head = open(path, encoding="utf-8").read(8000)
    except Exception:
        return None
    m = re.search(r"^---\s*$(.*?)^---\s*$", head, re.S | re.M)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^\s*([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", line)
        if kv:
            fm[kv.group(1)] = kv.group(2)
    if "status" not in fm:
        return None
    fm["_path"] = path
    fm["_mtime"] = os.path.getmtime(path)
    return fm


def read_lease(marker_path):
    """Return (runner, epoch_ts) from the lock file, or (None, 0)."""
    try:
        with open(marker_path + ".lock", encoding="utf-8") as f:
            runner = f.readline().strip()
            ts = float(f.readline().strip() or 0)
        return runner or None, ts
    except (FileNotFoundError, ValueError):
        return None, 0.0


def lease_state(runner, ts):
    if not runner:
        return "free"
    return "fresh" if (time.time() - ts) < LEASE_TTL else "stale"


def collect(root):
    loops = []
    for path in sorted(glob.glob(os.path.join(root, "plans", "loop", "*.md"))):
        fm = parse_marker(path)
        if not fm:
            continue
        runner, ts = read_lease(path)
        fm["_leaseRunner"] = runner
        fm["_leaseTs"] = ts
        fm["_lease"] = lease_state(runner, ts)
        loops.append(fm)
    order = {"active": 0, "paused": 1, "done": 2}
    loops.sort(key=lambda fm: (order.get(fm.get("status", ""), 3), fm.get("goalId", "")))
    return loops


def _age(seconds):
    seconds = int(seconds)
    if seconds < 90:
        return f"{seconds}s"
    if seconds < 5400:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"


def print_terminal(loops, root):
    if not loops:
        print("no goal-loops found (plans/loop/*.md)")
        return
    now = time.time()
    for fm in loops:
        name = fm.get("goalId") or os.path.basename(fm["_path"])[:-3]
        status = fm.get("status", "?")
        cycle = fm.get("cycle", "?")
        max_c = fm.get("maxCycles")
        cyc = f"cycle {cycle}/{max_c}" if max_c else f"cycle {cycle}"
        lease = fm["_lease"]
        if lease == "free":
            run = "runner: none (lease free)"
        else:
            run = f"runner: {fm['_leaseRunner']} ({lease}, {_age(now - fm['_leaseTs'])} ago)"
        bits = [f"[{status}]", name, cyc, run]
        counts = [fm.get(k) for k in ("backlogOpen", "backlogInProgress", "backlogDone")]
        if any(c is not None for c in counts):
            bits.append("backlog open/wip/done: " + "/".join(c or "0" for c in counts))
        if fm.get("backlogBlocked"):
            bits.append(f"parked: {fm['backlogBlocked']}")
        if fm.get("deliveryMode"):
            bits.append(f"delivery: {fm['deliveryMode']}")
        if fm.get("linearProject"):
            bits.append(f"linear: {fm['linearProject']}")
        print("  ".join(bits))
        if fm.get("goal"):
            print(f"    goal: {fm['goal']}")
        if fm.get("lastOutcome"):
            print(f"    last: {fm['lastOutcome']}")
        print(f"    updated: {_age(now - fm['_mtime'])} ago · marker: {os.path.relpath(fm['_path'], root)}")


HTML_PAGE = """<!doctype html>
<meta charset="utf-8">
<meta http-equiv="refresh" content="30">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Loobster — loop status</title>
<style>
  :root {{ --bg:#fff; --fg:#1f2328; --muted:#59636e; --card:#f6f8fa; --line:#d1d9e0;
           --active:#1a7f37; --paused:#9a6700; --done:#59636e; --stale:#cf222e; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#0d1117; --fg:#f0f6fc; --muted:#9198a1; --card:#151b23; --line:#3d444d;
             --active:#3fb950; --paused:#d29922; --done:#9198a1; --stale:#f85149; }} }}
  body {{ margin:0; padding:24px; background:var(--bg); color:var(--fg);
         font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; }}
  h1 {{ font-size:16px; margin:0 0 4px; }} h1 span {{ color:var(--stale); }}
  .sub {{ color:var(--muted); margin-bottom:20px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:8px;
           padding:14px 16px; margin-bottom:14px; max-width:860px; }}
  .row {{ display:flex; flex-wrap:wrap; gap:8px 16px; align-items:baseline; }}
  .pill {{ padding:1px 10px; border-radius:999px; font-weight:600; font-size:12px;
           border:1px solid currentColor; }}
  .active {{ color:var(--active); }} .paused {{ color:var(--paused); }}
  .done {{ color:var(--done); }} .stale,.lost {{ color:var(--stale); }}
  .goal {{ font-weight:600; margin:6px 0 2px; }}
  .kv {{ color:var(--muted); }} .kv b {{ color:var(--fg); font-weight:600; }}
  .bar {{ height:6px; border-radius:3px; background:var(--line); overflow:hidden;
          margin-top:8px; max-width:420px; }}
  .bar i {{ display:block; height:100%; background:var(--active); }}
  .age {{ color:var(--muted); font-size:12px; margin-top:6px; }}
</style>
<h1>&#129438; Loobster <span>loop status</span></h1>
<div class="sub">generated {generated} &middot; auto-refreshes every 30s &middot; regenerated at each cycle checkpoint</div>
{cards}
<script>
  // Live ages: recompute from embedded epochs so a stale page is visibly stale.
  document.querySelectorAll('[data-ts]').forEach(el => {{
    const s = Math.max(0, (Date.now()/1000) - Number(el.dataset.ts));
    const t = s < 90 ? Math.round(s)+'s' : s < 5400 ? Math.round(s/60)+'m' : (s/3600).toFixed(1)+'h';
    el.textContent = el.textContent.replace('{{age}}', t);
  }});
</script>
"""

CARD = """<div class="card">
  <div class="row">
    <span class="pill {status_cls}">{status}</span>
    <span class="kv">goalId <b>{name}</b></span>
    <span class="kv">cycle <b>{cycle}</b></span>
    <span class="kv">runner <b class="{lease_cls}">{lease}</b></span>
  </div>
  <div class="goal">{goal}</div>
  {backlog}
  {outcome}
  <div class="age" data-ts="{mtime}">checkpointed {{age}} ago &middot; {path}</div>
</div>"""


def build_html(loops, root):
    cards = []
    for fm in loops:
        name = html.escape(fm.get("goalId") or os.path.basename(fm["_path"])[:-3])
        status = html.escape(fm.get("status", "?"))
        cycle = html.escape(fm.get("cycle", "?"))
        if fm.get("maxCycles"):
            cycle += f" / {html.escape(fm['maxCycles'])}"
        if fm["_lease"] == "free":
            lease, lease_cls = "none (lease free)", "done"
        else:
            lease = f"{html.escape(fm['_leaseRunner'])} ({fm['_lease']})"
            lease_cls = "active" if fm["_lease"] == "fresh" else "stale"
        counts = [fm.get(k) for k in ("backlogOpen", "backlogInProgress", "backlogDone")]
        backlog = ""
        if any(c is not None for c in counts):
            # Counts are written free-form by the model; tolerate garbage as 0
            # rather than letting one bad value kill every future board build.
            o, w, d = (_to_int(c) or 0 for c in counts)
            total = max(1, o + w + d)
            parked = _to_int(fm.get("backlogBlocked"))
            parked_txt = f' &middot; <b class="paused">{parked}</b> parked' if parked else ""
            backlog = (f'<div class="kv">backlog: <b>{o}</b> open &middot; <b>{w}</b> in progress '
                       f'&middot; <b>{d}</b> done{parked_txt}</div>'
                       f'<div class="bar"><i style="width:{100 * d // total}%"></i></div>')
        extra = []
        if fm.get("deliveryMode"):
            extra.append(f'delivery <b>{html.escape(fm["deliveryMode"])}</b>')
        if fm.get("linearProject"):
            extra.append(f'linear <b>{html.escape(fm["linearProject"])}</b>')
        if extra:
            backlog += f'<div class="kv">{" &middot; ".join(extra)}</div>'
        outcome = ""
        if fm.get("lastOutcome"):
            outcome = f'<div class="kv">last: <b>{html.escape(fm["lastOutcome"])}</b></div>'
        cards.append(CARD.format(
            status=status, status_cls=html.escape(fm.get("status", "done")),
            name=name, cycle=cycle, lease=lease, lease_cls=lease_cls,
            goal=html.escape(fm.get("goal", "")), backlog=backlog, outcome=outcome,
            mtime=int(fm["_mtime"]), path=html.escape(os.path.basename(fm["_path"])),
        ))
    if not cards:
        cards = ['<div class="card"><div class="goal">No goal-loops found.</div>'
                 '<div class="kv">Start one with /loobster:loop &lt;goal&gt;</div></div>']
    page = HTML_PAGE.format(
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        cards="\n".join(cards),
    )
    out = os.path.join(root, "plans", "loop", "status.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    return out


def main(argv):
    root = "."
    build = False
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == "build":
            build = True
        elif a == "--root" and args:
            root = args.pop(0)
        elif a in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        else:
            print(f"error: unknown argument '{a}' (see --help)")
            return 2
    root = _loops_root(root)
    loops = collect(root)
    print_terminal(loops, root)
    if build:
        if not os.path.isdir(os.path.join(root, "plans", "loop")):
            # Never create directories on a project that has no loops (cwd hygiene).
            print("nothing to build: no plans/loop/ directory")
            return 0
        out = build_html(loops, root)
        print(f"wrote {os.path.relpath(out, root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
