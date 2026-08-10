#!/usr/bin/env bash
# Tests for bin/loop-rearm.py (the Stop hook that keeps an active goal-loop running).
# Verifies: blocks only when a loop is active; bounded progress-aware re-blocking
# (re-blocks inside a stop chain, allows after LOOBSTER_LOOP_REARM_MAX consecutive
# no-progress nudges, resets on cycle progress / a fresh chain); kill switch;
# status:done/paused allow; fails open on bad input / no marker.
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

# 3. stop_hook_active=true -> still BLOCK (bounded re-block replaced the one-nudge rule).
d="$(mk active)"
out="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":true}" | "$HOOK")"
{ blocks "$out"; } && ok "stop_hook_active -> still blocks (bounded re-block)" || no "in-chain re-block" "$out"; rmtree "$d"

# 3b. Exhaustion: MAX consecutive in-chain nudges with no progress -> allow (wedge guard).
d="$(mk active)"
o1="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":true}" | LOOBSTER_LOOP_REARM_MAX=2 "$HOOK")"
o2="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":true}" | LOOBSTER_LOOP_REARM_MAX=2 "$HOOK")"
o3="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":true}" | LOOBSTER_LOOP_REARM_MAX=2 "$HOOK")"
{ blocks "$o1" && blocks "$o2" && ! blocks "$o3"; } \
  && ok "no progress x MAX -> allow (bounded)" || no "bounded exhaustion" "o1=$o1 o2=$o2 o3=$o3"; rmtree "$d"

# 3c. Progress (cycle bump) resets the counter -> blocks again after exhaustion.
d="$(mk active)"
echo "{\"cwd\":\"$d\",\"stop_hook_active\":true}" | LOOBSTER_LOOP_REARM_MAX=1 "$HOOK" >/dev/null
o_exh="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":true}" | LOOBSTER_LOOP_REARM_MAX=1 "$HOOK")"
printf -- '---\nstatus: active\ngoalId: demo\ncycle: 7\n---\ngoal\n' > "$d/plans/loop/demo.md"
o_prog="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":true}" | LOOBSTER_LOOP_REARM_MAX=1 "$HOOK")"
{ ! blocks "$o_exh" && blocks "$o_prog"; } \
  && ok "cycle progress resets counter -> block again" || no "progress reset" "exh=$o_exh prog=$o_prog"; rmtree "$d"

# 3d. A fresh stop chain (stop_hook_active=false) resets the counter after exhaustion.
d="$(mk active)"
echo "{\"cwd\":\"$d\",\"stop_hook_active\":true}" | LOOBSTER_LOOP_REARM_MAX=1 "$HOOK" >/dev/null
o_exh="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":true}" | LOOBSTER_LOOP_REARM_MAX=1 "$HOOK")"
o_fresh="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":false}" | LOOBSTER_LOOP_REARM_MAX=1 "$HOOK")"
{ ! blocks "$o_exh" && blocks "$o_fresh"; } \
  && ok "fresh chain resets counter -> block again" || no "fresh-chain reset" "exh=$o_exh fresh=$o_fresh"; rmtree "$d"

# 3f. Nudge budgets are PER SESSION: exhausting session A must not spend session B's.
d="$(mk active)"
echo "{\"cwd\":\"$d\",\"stop_hook_active\":true,\"session_id\":\"sessA\"}" | LOOBSTER_LOOP_REARM_MAX=1 "$HOOK" >/dev/null
oA="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":true,\"session_id\":\"sessA\"}" | LOOBSTER_LOOP_REARM_MAX=1 "$HOOK")"
oB="$(echo "{\"cwd\":\"$d\",\"stop_hook_active\":true,\"session_id\":\"sessB\"}" | LOOBSTER_LOOP_REARM_MAX=1 "$HOOK")"
{ ! blocks "$oA" && blocks "$oB"; } && ok "per-session budgets (A exhausted, B still blocks)" || no "session keying" "A=$oA B=$oB"; rmtree "$d"

# 3e. Session cwd is a SUBDIRECTORY of the project -> markers still found (root walk-up).
d="$(mk active)"; mkdir -p "$d/apps/web"
out="$(echo "{\"cwd\":\"$d/apps/web\"}" | "$HOOK")"
{ blocks "$out"; } && ok "subdir cwd -> still blocks (walks up to plans/loop)" || no "subdir walk-up" "$out"; rmtree "$d"

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

# 7. Marker file with NO frontmatter but a body line starting "status: active" -> allow.
#    A stray prose line must NOT wedge the session (H05 fail-open hole).
d="$(mktemp -d)"; mkdir -p "$d/plans/loop"
printf 'no frontmatter here\nstatus: active in prose\n' > "$d/plans/loop/nofm.md"
out="$(echo "{\"cwd\":\"$d\"}" | "$HOOK")"
{ ! blocks "$out"; } && ok "no-frontmatter marker -> allow (fail open)" || no "no-frontmatter fail-open" "$out"; rmtree "$d"

echo "----"; echo "$PASS passed, $FAIL failed"; [ "$FAIL" -eq 0 ]
