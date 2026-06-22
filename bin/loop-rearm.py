#!/usr/bin/env python3
"""Stop hook — keep an active Loobster goal-loop running across turn boundaries.

A goal-loop's whole point is to run to a real exit condition (goal met / backlog
empty / maxCycles / budget) or an escalation — NOT to pause at a "clean milestone"
and ask "keep going?". This hook is the safety net for that: when a goal-loop is
marked active and has not reached an exit, it refuses the stop and tells the model
to resume (reclaim any stale in-progress task, continue from the top of the backlog).

Durable marker: `plans/loop/<slug>.md` frontmatter `status: active|done`. The loop
sets `active` at setup and `done` on exit/escalation. To stop a loop by hand, set
`status: done` (or delete the file), or set LOOBSTER_LOOP_REARM=0.

SAFETY:
  - Honors `stop_hook_active` — never re-blocks inside a hook-induced continuation
    (prevents infinite Stop loops). It nudges once per natural stop; the durable
    driver (scheduler/cron) covers hard crashes the Stop event can't catch.
  - Kill switch: LOOBSTER_LOOP_REARM=0 (or false/off).
  - Fails OPEN: any error → allow the stop. Never wedge a session.
"""
import sys, json, glob, os, re

def allow():           # let the session stop
    sys.exit(0)

def block(reason):     # refuse the stop; model continues with `reason`
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)

def main():
    if os.environ.get("LOOBSTER_LOOP_REARM", "1").lower() in ("0", "false", "off"):
        allow()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        allow()
    # Already continuing because of a Stop hook → don't re-block (infinite-loop guard).
    if payload.get("stop_hook_active"):
        allow()
    cwd = payload.get("cwd") or os.getcwd()
    active = []
    for path in glob.glob(os.path.join(cwd, "plans", "loop", "*.md")):
        try:
            head = open(path, encoding="utf-8").read(4000)
        except Exception:
            continue
        m = re.search(r"^---\s*$(.*?)^---\s*$", head, re.S | re.M)
        block_txt = m.group(1) if m else head
        st = re.search(r"^\s*status\s*:\s*(\S+)", block_txt, re.M)
        if st and st.group(1).strip().lower() == "active":
            slug = re.search(r"^\s*goalId\s*:\s*(\S+)", block_txt, re.M)
            active.append(slug.group(1) if slug else os.path.basename(path)[:-3])
    if not active:
        allow()
    names = ", ".join(active)
    block(
        f"A Loobster goal-loop is still active ({names}: status: active in plans/loop/) and has "
        f"NOT reached an exit condition. Do not stop at a milestone or to ask 'keep going'. "
        f"Resume the loop now: (1) reclaim any task left in_progress with a stale/absent heartbeat "
        f"(check what already landed; continue, don't redo), (2) consume new signals, (3) continue "
        f"from the highest-scored open task. Only stop on a real exit condition (goal met, backlog "
        f"empty with no justified work, maxCycles, or --budget) or an escalation. "
        f"IMPORTANT: if you stopped for a human approval gate (the final commit/push) or to escalate "
        f"unresolved/sensitive work, that is a LEGITIMATE stop — set `status: done` (or `paused`) in the "
        f"marker and stop; NEVER push past an approval to keep the loop alive. To end the loop, set "
        f"`status: done` in its plans/loop/<slug>.md (or set LOOBSTER_LOOP_REARM=0)."
    )

if __name__ == "__main__":
    main()
