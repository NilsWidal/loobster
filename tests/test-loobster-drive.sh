#!/usr/bin/env bash
# Tests for bin/loobster-drive.sh (external cross-tool loop driver).
# Verifies: drives while active and stops when the marker flips to done; a paused
# marker stops the driver WITHOUT invoking (gates sacred); --max caps runaway
# invocations; default prompt is built from the marker goal; dry-run; usage errors.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRIVE="$ROOT/bin/loobster-drive.sh"
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }
rmtree(){ python3 -c "import shutil,sys;shutil.rmtree(sys.argv[1],ignore_errors=True)" "$1"; }

mkmarker(){ # mkmarker <dir> <status>
  mkdir -p "$1/plans/loop"
  printf -- '---\nstatus: %s\ngoalId: demo\ngoal: ship the thing\n---\ncriteria\n' "$2" \
    > "$1/plans/loop/demo.md"; }

# 1. Drives while active; stops cleanly when the invoked "agent" flips the marker to done.
d="$(mktemp -d)"; mkmarker "$d" active
# Fake agent CLI: log the invocation; flip the marker to done on the 2nd call.
cat > "$d/fake.sh" <<EOF
#!/usr/bin/env bash
echo "\$1" >> "$d/calls.log"
if [ "\$(wc -l < "$d/calls.log")" -ge 2 ]; then
  printf -- '---\nstatus: done\ngoalId: demo\ngoal: ship the thing\n---\n' > "$d/plans/loop/demo.md"
fi
EOF
chmod +x "$d/fake.sh"
out="$(LOOBSTER_DRIVE_CMD="$d/fake.sh {prompt}" "$DRIVE" "$d/plans/loop/demo.md" --interval 0 --max 10)"; rc=$?
calls="$(wc -l < "$d/calls.log" | tr -d ' ')"
{ [ "$rc" = 0 ] && [ "$calls" = 2 ] && echo "$out" | grep -q "DONE"; } \
  && ok "drives while active, stops on done (2 calls)" || no "active->done" "rc=$rc calls=$calls out=$out"
rmtree "$d"

# 2. Paused marker -> stops WITHOUT invoking (never supplies turns past a gate).
d="$(mktemp -d)"; mkmarker "$d" paused
out="$(LOOBSTER_DRIVE_CMD="touch $d/invoked" "$DRIVE" "$d/plans/loop/demo.md" --interval 0)"; rc=$?
{ [ "$rc" = 0 ] && [ ! -e "$d/invoked" ] && echo "$out" | grep -q "PAUSED"; } \
  && ok "paused -> stop without invoking (gate sacred)" || no "paused gate" "rc=$rc out=$out"
rmtree "$d"

# 3. --max caps invocations when the loop never exits.
d="$(mktemp -d)"; mkmarker "$d" active
out="$(LOOBSTER_DRIVE_CMD="echo run >> $d/calls.log ; true {prompt}" "$DRIVE" "$d/plans/loop/demo.md" --interval 0 --max 3)"; rc=$?
calls="$(wc -l < "$d/calls.log" | tr -d ' ')"
{ [ "$rc" = 1 ] && [ "$calls" = 3 ]; } && ok "--max caps runaway driving" || no "--max cap" "rc=$rc calls=$calls"
rmtree "$d"

# 4. Default prompt is built from the marker goal (dry-run shows it, invokes nothing).
d="$(mktemp -d)"; mkmarker "$d" active
out="$("$DRIVE" "$d/plans/loop/demo.md" --dry-run)"; rc=$?
{ [ "$rc" = 0 ] && echo "$out" | grep -q "/loobster:loop ship the thing"; } \
  && ok "default prompt from goal (dry-run)" || no "default prompt" "rc=$rc out=$out"
out="$("$DRIVE" "$d/plans/loop/demo.md" --tool codex --dry-run)"
echo "$out" | grep -q '\$loop ship the thing' && ok "codex prompt form" || no "codex prompt" "$out"
rmtree "$d"

# 4b. A hostile/awkward goal (quotes, semicolons) arrives as ONE argument — no
#     shell injection, no parse error, prompt intact.
d="$(mktemp -d)"; mkdir -p "$d/plans/loop"
printf -- '---\nstatus: active\ngoalId: demo\ngoal: dont'"'"'t stop; touch %s/INJECTED\n---\n' "$d" \
  > "$d/plans/loop/demo.md"
cat > "$d/fake.sh" <<EOF
#!/usr/bin/env bash
printf '%s' "\$1" > "$d/arg1.txt"
printf -- '---\nstatus: done\ngoalId: demo\ngoal: x\n---\n' > "$d/plans/loop/demo.md"
EOF
chmod +x "$d/fake.sh"
LOOBSTER_DRIVE_CMD="$d/fake.sh {prompt}" "$DRIVE" "$d/plans/loop/demo.md" --interval 0 --max 3 >/dev/null; rc=$?
{ [ "$rc" = 0 ] && [ ! -e "$d/INJECTED" ] && grep -q "touch $d/INJECTED" "$d/arg1.txt"; } \
  && ok "hostile goal -> one argument, no injection" || no "injection guard" "rc=$rc arg1=$(cat "$d/arg1.txt" 2>/dev/null)"
rmtree "$d"

# 5. Usage errors: missing marker; unknown option.
"$DRIVE" /nonexistent/marker.md >/dev/null 2>&1; [ $? = 2 ] && ok "missing marker -> exit 2" || no "missing marker" "rc=$?"
"$DRIVE" --bogus >/dev/null 2>&1; [ $? = 2 ] && ok "unknown option -> exit 2" || no "unknown option" "rc=$?"
# A value-taking flag with no value must error out, not spin the parse loop forever.
"$DRIVE" some.md --interval >/dev/null 2>&1; [ $? = 2 ] && ok "flag missing value -> exit 2 (no hang)" || no "missing value" "rc=$?"

echo "----"; echo "$PASS passed, $FAIL failed"; [ "$FAIL" -eq 0 ]
