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

SESSION SCOPING (multiple loops in one worktree):
  Claude Code doesn't expose a session's own id in-session, so a loop can't tag its
  marker with an owner. Instead the loop stamps each turn's output with a sentinel
  `[[loobster-loop goalId=<slug>]]`; the Stop payload carries that last message, so
  this hook blocks only for the loop(s) the CURRENT session named -- a session whose
  own loop finished can stop even if a sibling loop (another session's) is still
  active. No sentinel in the message -> legacy behavior (block for any active loop).
  Cleanest of all: give each concurrent loop its own git worktree, and cwd isolates
  them completely.

RE-BLOCK POLICY (bounded, progress-aware — not one-nudge):
  The old behavior allowed any stop with `stop_hook_active` set, so the hook could
  nudge exactly once per natural stop; a model that stopped twice in a row killed
  the loop until the next cron fired. Instead, the hook now re-blocks REPEATEDLY,
  bounded by a progress counter kept in `plans/loop/.rearm-state.json`:
    - Progress fingerprint = each active marker's (cycle, runnerHeartbeatAt).
      Any change → the loop is genuinely advancing → counter resets to 0.
    - A fresh stop chain (stop_hook_active absent) also resets the counter —
      each new turn earns a fresh budget of nudges.
    - After LOOBSTER_LOOP_REARM_MAX consecutive blocks with NO progress
      (default 5), the hook allows the stop: a loop that won't advance after
      five nudges is wedged, and wedged sessions fail OPEN. (Claude Code
      additionally force-stops after 8 consecutive Stop-hook blocks without
      progress — keep LOOBSTER_LOOP_REARM_MAX under 8 so WE decide to fail
      open, rather than being overridden.)

SAFETY:
  - Bounded: the counter above guarantees no infinite Stop loop even though we
    intentionally block while `stop_hook_active` is set.
  - Kill switch: LOOBSTER_LOOP_REARM=0 (or false/off).
  - Fails OPEN: any error (including state-file I/O) → allow the stop. Never
    wedge a session.
"""
import sys, json, glob, os, re

DEFAULT_MAX_BLOCKS = 5


def allow():           # let the session stop
    sys.exit(0)


def block(reason):     # refuse the stop; model continues with `reason`
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def _loops_root(cwd):
    """Nearest ancestor of cwd (inclusive, bounded) that has a plans/loop dir.

    A session started in a subdirectory of the repo would otherwise never see the
    markers and silently stop re-arming — the glob must anchor at the project
    root, not wherever the session happens to sit."""
    p = os.path.abspath(cwd)
    for _ in range(10):
        if os.path.isdir(os.path.join(p, "plans", "loop")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return cwd


def _owned_goalids(payload):
    """goalIds this session named in its last turn via a `[[loobster-loop goalId=X]]`
    sentinel (loop.md prints it each checkpoint). Empty set = the session didn't say,
    so the caller keeps the legacy "any active loop" behavior. This is how the hook
    scopes to THIS session's loop when several loops share one worktree: Claude Code
    doesn't expose the session's own id in-session, but the Stop payload carries the
    turn's last assistant message, which the loop can stamp."""
    msg = payload.get("last_assistant_message") or ""
    return set(re.findall(r"\[\[loobster-loop\s+goalId=([^\s\]]+)\]\]", msg))


def _active_loops(cwd):
    """Return [(name, fingerprint)] for every marker with frontmatter status: active."""
    found = []
    for path in sorted(glob.glob(os.path.join(cwd, "plans", "loop", "*.md"))):
        try:
            head = open(path, encoding="utf-8").read(4000)
        except Exception:
            continue
        m = re.search(r"^---\s*$(.*?)^---\s*$", head, re.S | re.M)
        if not m:
            # No frontmatter fence -> not a real loop marker. Fail OPEN (allow the
            # stop); never scan the whole body, or a stray "status: active" line
            # in prose would wedge the session.
            continue
        block_txt = m.group(1)
        st = re.search(r"^\s*status\s*:\s*(\S+)", block_txt, re.M)
        if not (st and st.group(1).strip().lower() == "active"):
            continue
        slug = re.search(r"^\s*goalId\s*:\s*(\S+)", block_txt, re.M)
        name = slug.group(1) if slug else os.path.basename(path)[:-3]
        cyc = re.search(r"^\s*cycle\s*:\s*(\S+)", block_txt, re.M)
        hb = re.search(r"^\s*runnerHeartbeatAt\s*:\s*(\S+)", block_txt, re.M)
        fp = f"{name}:{cyc.group(1) if cyc else '?'}:{hb.group(1) if hb else '?'}"
        found.append((name, fp))
    return found


def _count_block(cwd, session, fingerprint, in_chain, max_blocks):
    """Bump this session's consecutive-no-progress counter; return blocks used so
    far (before this one), or None if state I/O failed (caller falls back to
    one-nudge). Keyed by session_id: two sessions on one worktree (the lease
    exists exactly for that) must not reset or pre-spend each other's budget."""
    state_path = os.path.join(cwd, "plans", "loop", ".rearm-state.json")
    try:
        try:
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}
        if not isinstance(state, dict):
            state = {}
        entry = state.get(session)
        if not isinstance(entry, dict) or entry.get("fingerprint") != fingerprint or not in_chain:
            blocks = 0                     # progress, or a fresh stop chain
        else:
            blocks = int(entry.get("blocks", 0))
        if blocks >= max_blocks:
            return blocks
        state[session] = {"fingerprint": fingerprint, "blocks": blocks + 1}
        if len(state) > 16:                # prune dead sessions' leftovers
            state = {session: state[session]}
        tmp = state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, state_path)
        return blocks
    except Exception:
        return None


def main():
    if os.environ.get("LOOBSTER_LOOP_REARM", "1").lower() in ("0", "false", "off"):
        allow()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        allow()
    cwd = _loops_root(payload.get("cwd") or os.getcwd())
    active = _active_loops(cwd)
    if not active:
        allow()

    # Scope to the loop(s) THIS session is driving, when it told us (multi-loop-in-one-
    # worktree). A session whose own loop is done/paused must be free to stop even if a
    # SIBLING loop (another session's) is still active. If the session didn't stamp a
    # sentinel, keep the legacy behavior: block for any active loop (no regression).
    owned = _owned_goalids(payload)
    if owned:
        mine = [(n, fp) for (n, fp) in active if n in owned]
        if not mine:
            allow()                    # my loop(s) aren't active; siblings aren't mine
        active = mine

    try:
        max_blocks = int(os.environ.get("LOOBSTER_LOOP_REARM_MAX", DEFAULT_MAX_BLOCKS))
    except ValueError:
        max_blocks = DEFAULT_MAX_BLOCKS
    in_chain = bool(payload.get("stop_hook_active"))
    session = str(payload.get("session_id") or "default")
    fingerprint = "|".join(fp for _, fp in active)
    used = _count_block(cwd, session, fingerprint, in_chain, max_blocks)
    if used is None:
        # State bookkeeping failed → legacy one-nudge behavior (never risk an
        # unbounded block loop without a working counter).
        if in_chain:
            allow()
        used = 0
    elif used >= max_blocks:
        # No progress after max_blocks nudges → the loop is wedged; fail OPEN.
        allow()

    names = ", ".join(n for n, _ in active)
    block(
        f"A Loobster goal-loop is still active ({names}: status: active in plans/loop/) and has "
        f"NOT reached an exit condition. Do not stop at a milestone or to ask 'keep going'. "
        f"Resume the loop now: (1) reclaim any task left in_progress with a stale/absent heartbeat "
        f"(check what already landed; continue, don't redo), (2) consume new signals, (3) continue "
        f"from the highest-scored open task, (4) re-arm your ScheduleWakeup re-entry if it already fired. "
        f"Only stop on a real exit condition (goal met, backlog empty with no justified work, maxCycles, "
        f"or --budget) or an escalation. [rearm nudge {used + 1}/{max_blocks} — resets on cycle progress] "
        f"IMPORTANT: if you stopped for a human approval gate (the final commit/push) or to escalate "
        f"unresolved/sensitive work, that is a LEGITIMATE stop — set `status: done` (or `paused`) in the "
        f"marker and stop; NEVER push past an approval to keep the loop alive. To end the loop, set "
        f"`status: done` in its plans/loop/<slug>.md (or set LOOBSTER_LOOP_REARM=0)."
    )


if __name__ == "__main__":
    main()
