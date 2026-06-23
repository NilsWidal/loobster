#!/usr/bin/env bash
# Tests for bin/loop-lease.py — the atomic single-runner lease for goal-loops.
# Verifies: acquire/held/refresh/release/takeover/status with real exit codes.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LEASE="$ROOT/bin/loop-lease.py"
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

tmp="$(mktemp -d)"; mkdir -p "$tmp/plans/loop"
M="$tmp/plans/loop/demo.md"
printf -- '---\nstatus: active\ngoalId: demo\n---\n' > "$M"

# 1. Acquire on a free lease -> exit 0, prints acquired.
out="$(python3 "$LEASE" acquire "$M" runnerA)"; rc=$?
{ [ "$rc" = 0 ] && echo "$out" | grep -q acquired; } && ok "acquire free -> acquired" || no "acquire free" "rc=$rc out=$out"

# 2. A different runner cannot acquire while held (fresh) -> exit 3, held.
out="$(python3 "$LEASE" acquire "$M" runnerB)"; rc=$?
{ [ "$rc" = 3 ] && echo "$out" | grep -qi held; } && ok "second runner -> held (exit 3)" || no "held check" "rc=$rc out=$out"

# 3. The holder can refresh.
out="$(python3 "$LEASE" refresh "$M" runnerA)"; rc=$?
[ "$rc" = 0 ] && ok "holder refresh -> ok" || no "refresh" "rc=$rc out=$out"

# 4. A non-holder cannot refresh -> exit 3.
out="$(python3 "$LEASE" refresh "$M" runnerB)"; rc=$?
[ "$rc" = 3 ] && ok "non-holder refresh -> 3" || no "refresh non-holder" "rc=$rc out=$out"

# 5. Release by holder frees it; another runner can then acquire.
python3 "$LEASE" release "$M" runnerA >/dev/null
out="$(python3 "$LEASE" acquire "$M" runnerB)"; rc=$?
{ [ "$rc" = 0 ] && echo "$out" | grep -q acquired; } && ok "after release, new acquire works" || no "post-release acquire" "rc=$rc out=$out"

# 6. Stale lease (ttl 0) can be taken over by another runner.
out="$(python3 "$LEASE" acquire "$M" runnerC --ttl 0)"; rc=$?
{ [ "$rc" = 0 ] && echo "$out" | grep -qi "took over"; } && ok "stale lease -> taken over" || no "stale takeover" "rc=$rc out=$out"

# 7. status reports the current holder.
out="$(python3 "$LEASE" status "$M")"; rc=$?
{ [ "$rc" = 0 ] && echo "$out" | grep -q "runner=runnerC"; } && ok "status reports holder" || no "status" "rc=$rc out=$out"

rm -rf "$tmp"
echo "----"; echo "$PASS passed, $FAIL failed"; [ "$FAIL" -eq 0 ]
