#!/usr/bin/env bash
# Tests for bin/loop-status.py (cross-tool loop status: terminal + status.html).
# Verifies: renders active/paused/done markers + lease freshness + backlog counts;
# builds a self-contained status.html; no cwd pollution when plans/loop is absent;
# skips frontmatter-less files; --help works.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATUS="$ROOT/bin/loop-status.py"
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }
rmtree(){ python3 -c "import shutil,sys;shutil.rmtree(sys.argv[1],ignore_errors=True)" "$1"; }

mkfix(){ # fixture: one active loop (fresh lease + backlog counts), one done loop
  local d; d="$(mktemp -d)"; mkdir -p "$d/plans/loop"
  cat > "$d/plans/loop/cov.md" <<'EOF'
---
status: active
goalId: cov
goal: Raise coverage
cycle: 4
maxCycles: 10
backlogOpen: 5
backlogInProgress: 1
backlogDone: 7
backlogBlocked: 2
deliveryMode: pr-lane
linearProject: CAR
lastOutcome: cycle 4 partial
---
criteria
EOF
  python3 -c "import time,sys;open(sys.argv[1],'w').write('sess-a\n%d\n'%(int(time.time())-60))" \
    "$d/plans/loop/cov.md.lock"
  printf -- '---\nstatus: done\ngoalId: old\ngoal: Shipped\ncycle: 9\n---\n' > "$d/plans/loop/old.md"
  echo "$d"; }

# 1. Terminal output shows both loops, active first, with lease + backlog.
d="$(mkfix)"
out="$(python3 "$STATUS" --root "$d")"; rc=$?
{ [ "$rc" = 0 ] && echo "$out" | head -1 | grep -q '\[active\]' \
  && echo "$out" | grep -q 'cycle 4/10' && echo "$out" | grep -q 'sess-a (fresh' \
  && echo "$out" | grep -q '5/1/7' && echo "$out" | grep -q 'parked: 2' \
  && echo "$out" | grep -q 'delivery: pr-lane' && echo "$out" | grep -q 'linear: CAR' \
  && echo "$out" | grep -q '\[done\]'; } \
  && ok "terminal status (active first, lease, backlog, delivery, linear)" || no "terminal status" "rc=$rc out=$out"

# 2. build writes a self-contained status.html containing both goals + refresh meta.
out="$(python3 "$STATUS" build --root "$d")"; rc=$?
{ [ "$rc" = 0 ] && [ -f "$d/plans/loop/status.html" ] \
  && grep -q 'Raise coverage' "$d/plans/loop/status.html" \
  && grep -q 'http-equiv="refresh"' "$d/plans/loop/status.html" \
  && ! grep -qi 'src="http' "$d/plans/loop/status.html"; } \
  && ok "build -> self-contained status.html" || no "build html" "rc=$rc out=$out"

# 3. Stale lease is reported as stale.
python3 -c "import sys;open(sys.argv[1],'w').write('sess-a\n1000000\n')" "$d/plans/loop/cov.md.lock"
out="$(python3 "$STATUS" --root "$d")"
echo "$out" | grep -q 'sess-a (stale' && ok "stale lease reported" || no "stale lease" "$out"
rmtree "$d"

# 4. No plans/loop dir -> no build, no directory created (cwd hygiene).
e="$(mktemp -d)"
out="$(python3 "$STATUS" build --root "$e")"; rc=$?
{ [ "$rc" = 0 ] && [ ! -d "$e/plans" ]; } && ok "no plans/loop -> no pollution" || no "cwd hygiene" "rc=$rc"
rmtree "$e"

# 5. Frontmatter-less file is skipped, not a crash.
d="$(mktemp -d)"; mkdir -p "$d/plans/loop"
printf 'not a marker\nstatus: active\n' > "$d/plans/loop/junk.md"
out="$(python3 "$STATUS" --root "$d")"; rc=$?
{ [ "$rc" = 0 ] && echo "$out" | grep -q 'no goal-loops found'; } \
  && ok "frontmatter-less file skipped" || no "junk marker" "rc=$rc out=$out"
rmtree "$d"

# 6. Run from a SUBDIRECTORY -> markers still found (root walk-up, matches loop-rearm).
d="$(mkfix)"; mkdir -p "$d/apps/web"
out="$(cd "$d/apps/web" && python3 "$STATUS" build)"; rc=$?
{ [ "$rc" = 0 ] && echo "$out" | grep -q '\[active\]' && [ -f "$d/plans/loop/status.html" ]; } \
  && ok "subdir cwd -> walks up to plans/loop" || no "subdir walk-up" "rc=$rc out=$out"
rmtree "$d"

# 7. Garbage backlog counts (free-form model output) must not crash the build.
d="$(mktemp -d)"; mkdir -p "$d/plans/loop"
printf -- '---\nstatus: active\ngoalId: g\ngoal: x\ncycle: 1\nbacklogOpen: three\nbacklogDone: 2\n---\n' \
  > "$d/plans/loop/g.md"
out="$(python3 "$STATUS" build --root "$d" 2>&1)"; rc=$?
{ [ "$rc" = 0 ] && [ -f "$d/plans/loop/status.html" ]; } \
  && ok "garbage backlog count -> tolerated, board still builds" || no "garbage counts" "rc=$rc out=$out"
rmtree "$d"

# 8. --help exits 0 and prints usage.
python3 "$STATUS" --help | grep -q 'loop-status' && ok "--help" || no "--help" "no usage"

echo "----"; echo "$PASS passed, $FAIL failed"; [ "$FAIL" -eq 0 ]
