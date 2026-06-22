#!/usr/bin/env bash
# Tests for bin/loop-rearm.py (the Stop hook that keeps an active goal-loop running).
# Verifies: blocks only when a loop is active; honors stop_hook_active (no infinite
# loop); kill switch; status:done allows stop; fails open on bad input / no marker.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$ROOT/bin/loop-rearm.py"
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }
rmtree(){ python3 -c "import shutil,sys;shutil.rmtree(sys.argv[1],ignore_errors=True)" "$1"; }

mk(){ # mk <status> -> tmp dir with plans/loop/g.md at that status
  local d; d="$(mktemp -d)"; mkdir -p "$d/plans/loop"
  printf -- '---\nstatus: %s\ngoalId: demo\n---\ngoal\n' "$1" > "$d/plans/loop/demo.md"; echo "$d"; }
blocks(){ echo "$1" | grep -q '"decision":[[:space:]]*"block"'; }

# 1. No marker at all -> allow stop (fail open / unaffected projects).
empty="$(mktemp -d)"
out="$(echo "{\"cwd\":\"$empty\"}" | "$HOOK")"; rc=$?
{ [ -z "$out" ] && [ "$rc" = 0 ]; } && ok "no marker -> allow" || no "no marker" "rc=$rc out=$out"; rmtree "$empty"

# 2. Active loop -> block with a resume reason.
d="$(mk active)"
out="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":false}" | "$HOOK")"
{ blocks "$out" && echo "$out" | grep -qi "resume the loop"; } && ok "active -> block+resume" || no "active block" "$out"; rmtree "$d"

# 3. stop_hook_active=true -> allow (infinite-loop guard) even with an active loop.
d="$(mk active)"
out="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":true}" | "$HOOK")"
{ ! blocks "$out"; } && ok "stop_hook_active -> allow (no infinite loop)" || no "infinite-loop guard" "$out"; rmtree "$d"

# 4. status: done -> allow stop.
d="$(mk done)"
out="$(echo "{\"cwd\":\"$d\"}" | "$HOOK")"
{ ! blocks "$out"; } && ok "status:done -> allow" || no "done allow" "$out"; rmtree "$d"

# 4b. status: paused (awaiting a human approval gate) -> allow stop (gates stay sacred).
d="$(mk paused)"
out="$(echo "{\"cwd\":\"$d\"}" | "$HOOK")"
{ ! blocks "$out"; } && ok "status:paused -> allow (approval gate sacred)" || no "paused allow" "$out"; rmtree "$d"

# 5. Kill switch LOOBSTER_LOOP_REARM=0 -> allow even when active.
d="$(mk active)"
out="$(echo "{\"cwd\":\"$d\"}" | LOOBSTER_LOOP_REARM=0 "$HOOK")"
{ ! blocks "$out"; } && ok "LOOBSTER_LOOP_REARM=0 -> allow" || no "kill switch" "$out"; rmtree "$d"

# 6. Malformed stdin -> allow (fail open).
out="$(echo 'not json' | "$HOOK")"; rc=$?
{ ! blocks "$out" && [ "$rc" = 0 ]; } && ok "malformed stdin -> allow" || no "fail open" "rc=$rc out=$out"

echo "----"; echo "$PASS passed, $FAIL failed"; [ "$FAIL" -eq 0 ]
