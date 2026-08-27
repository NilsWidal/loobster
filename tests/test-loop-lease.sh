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

# 8. Concurrency: N runners racing to take over ONE stale lease -> exactly one wins.
#    This is the guarantee the docs make ("two racing instances cannot both win"),
#    and the exact path where the old remove()+create() double-won. We seed a
#    genuinely stale lock (backdated timestamp) and race with a NORMAL ttl, so the
#    first taker writes a fresh lock and every other racer must see it as held.
#    Racers start together on a barrier file and record their exit code.
race="$(mktemp -d)"; mkdir -p "$race/plans/loop"; RM="$race/plans/loop/race.md"
printf -- '---\nstatus: active\ngoalId: race\n---\n' > "$RM"
printf 'seed\n1000000000\n' > "$RM.lock"          # holder=seed, ts=year 2001 (stale)
for i in $(seq 1 12); do
  ( while [ ! -f "$race/go" ]; do :; done          # spin until the barrier drops
    python3 "$LEASE" acquire "$RM" "r$i"           # default ttl 3600
    echo "$?" > "$race/rc.$i" ) &
done
touch "$race/go"; wait
winners="$(cat "$race"/rc.* | grep -c '^0$')"
losers="$(cat "$race"/rc.* | grep -c '^3$')"
holders="$(python3 "$LEASE" status "$RM" | grep -c 'fresh runner=r')"
{ [ "$winners" = 1 ] && [ "$losers" = 11 ] && [ "$holders" = 1 ]; } \
  && ok "12 racers on a stale lease -> exactly one winner" \
  || no "concurrent takeover" "winners=$winners losers=$losers holders=$holders (want 1/11/1)"
rm -rf "$race"

# 8b. A leftover .steal gate file (a taker crashed mid-takeover) must not wedge the
#     next takeover: the flock is auto-released by the OS, so racers still resolve to
#     exactly one winner regardless of the stale gate file sitting there.
ag="$(mktemp -d)"; mkdir -p "$ag/plans/loop"; AGM="$ag/plans/loop/ag.md"
printf -- '---\nstatus: active\ngoalId: ag\n---\n' > "$AGM"
printf 'seed\n1000000000\n' > "$AGM.lock"          # stale lock
: > "$AGM.lock.steal"                                # leftover gate file, no live flock
for i in $(seq 1 8); do
  ( while [ ! -f "$ag/go" ]; do :; done
    python3 "$LEASE" acquire "$AGM" "a$i"; echo "$?" > "$ag/rc.$i" ) &
done
touch "$ag/go"; wait
aw="$(cat "$ag"/rc.* | grep -c '^0$')"
{ [ "$aw" = 1 ] && python3 "$LEASE" status "$AGM" | grep -q 'fresh runner=a'; } \
  && ok "leftover steal gate -> single winner (flock auto-released)" \
  || no "leftover gate wedge" "winners=$aw"
rm -rf "$ag"

# 9. refresh racing a takeover must never crash (was an unhandled FileNotFoundError
#    on a shared tmp name). Hammer both against one marker; every call exits 0 or 3.
rr="$(mktemp -d)"; mkdir -p "$rr/plans/loop"; RRM="$rr/plans/loop/rr.md"
printf 'inc\n1000000000\n' > "$RRM.lock"           # incumbent 'inc', stale
bad=0
for i in $(seq 1 30); do
  ( python3 "$LEASE" refresh "$RRM" inc >/dev/null 2>&1; echo $? >> "$rr/codes" ) &
  ( python3 "$LEASE" acquire "$RRM" "t$i" >/dev/null 2>&1; echo $? >> "$rr/codes" ) &
done
wait
grep -qvE '^(0|3)$' "$rr/codes" && bad=1
{ [ "$bad" = 0 ] && ! ls "$RRM".tmp* >/dev/null 2>&1; } \
  && ok "refresh vs takeover -> no crash, no leaked tmp" \
  || no "refresh/takeover race" "unexpected exit code or leftover tmp"
rm -rf "$rr"

# 10. newid: unique per call, and a FRESH id must NOT think it already holds a live
#     lease (the re-entry-collision bug: reusing a derivable id hit "already held").
id1="$(python3 "$LEASE" newid)"; id2="$(python3 "$LEASE" newid)"
{ [ -n "$id1" ] && [ "$id1" != "$id2" ]; } \
  && ok "newid is unique per call" || no "newid uniqueness" "id1=$id1 id2=$id2"
nt="$(mktemp -d)"; mkdir -p "$nt/plans/loop"; NM="$nt/plans/loop/n.md"
printf -- '---\nstatus: active\ngoalId: n\n---\n' > "$NM"
python3 "$LEASE" acquire "$NM" "$(python3 "$LEASE" newid)" >/dev/null   # live holder
out="$(python3 "$LEASE" acquire "$NM" "$(python3 "$LEASE" newid)")"; rc=$?  # re-entry
{ [ "$rc" = 3 ] && echo "$out" | grep -qi held; } \
  && ok "fresh-id re-entry backs off (held, exit 3)" \
  || no "re-entry collision" "rc=$rc out=$out"
rm -rf "$nt"

# 11. Cross-platform: the module must LOAD without fcntl (the Windows path) and newid
#     must not use os.uname. Mask fcntl, re-import, and exercise the portable helpers.
python3 - "$ROOT/bin/loop-lease.py" <<'PY'
import sys, importlib.util
sys.modules["fcntl"] = None            # make `import fcntl` raise ImportError
spec = importlib.util.spec_from_file_location("ll_nofcntl", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)             # must not raise (falls back to msvcrt / stub)
assert callable(m._lock_exclusive) and callable(m._unlock), "portable helpers missing"
assert "uname" not in open(sys.argv[1]).read(), "newid still uses os.uname (Unix-only)"
PY
[ $? = 0 ] && ok "loads without fcntl; no os.uname (Windows-safe)" || no "cross-platform" "module failed to load without fcntl"

rm -rf "$tmp"
echo "----"; echo "$PASS passed, $FAIL failed"; [ "$FAIL" -eq 0 ]
