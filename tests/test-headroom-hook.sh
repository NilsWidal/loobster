#!/usr/bin/env bash
# Tests for Option D — bin/headroom-compress.py (the headroom PostToolUse hook).
# The hook is ENABLED BY DEFAULT: it compresses when a local headroom is importable,
# no-ops (passthrough) when headroom isn't installed, and is disabled by LOOBSTER_HEADROOM=0.
# Verifies: default-on compresses, kill switch, graceful passthrough, size threshold.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$ROOT/bin/headroom-compress.py"
PASS=0
FAIL=0

big="$(python3 -c "print('x'*5000)")"
payload="{\"tool_name\":\"Read\",\"tool_response\":{\"output\":\"$big\"}}"
rmtree() { python3 -c "import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)" "$1"; }

# assert_empty <name> <env...> -- runs hook with given env, expects empty stdout + exit 0
assert_empty() {
  local name="$1"; shift
  local out rc
  out="$(echo "$payload" | env "$@" "$HOOK")"; rc=$?
  if [ -z "$out" ] && [ "$rc" -eq 0 ]; then
    echo "PASS: $name"; PASS=$((PASS+1))
  else
    echo "FAIL: $name (rc=$rc, out=${out:0:60})"; FAIL=$((FAIL+1))
  fi
}

# mock headroom module (compresses) on PYTHONPATH
mock="$(mktemp -d)"
cat > "$mock/headroom.py" <<'PY'
def compress(text, model=None):
    return "COMPRESSED:" + str(len(text))
PY

# 1. Default on, but headroom NOT installed -> passthrough (no-op without the dep).
assert_empty "default on + headroom absent -> passthrough"

# 2. Kill switch: LOOBSTER_HEADROOM=0 with headroom present -> passthrough (disabled).
out="$(echo "$payload" | env LOOBSTER_HEADROOM=0 PYTHONPATH="$mock" "$HOOK")"; rc=$?
if [ -z "$out" ] && [ "$rc" -eq 0 ]; then echo "PASS: LOOBSTER_HEADROOM=0 disables -> passthrough"; PASS=$((PASS+1)); else echo "FAIL: kill switch (rc=$rc, out=${out:0:60})"; FAIL=$((FAIL+1)); fi

# 3. Malformed stdin -> passthrough.
out="$(echo 'not json' | "$HOOK")"; rc=$?
if [ -z "$out" ] && [ "$rc" -eq 0 ]; then echo "PASS: malformed stdin -> passthrough"; PASS=$((PASS+1)); else echo "FAIL: malformed stdin (rc=$rc)"; FAIL=$((FAIL+1)); fi

# 4. Output below size threshold -> passthrough (even with headroom present).
small='{"tool_name":"Read","tool_response":{"output":"tiny"}}'
out="$(echo "$small" | env PYTHONPATH="$mock" "$HOOK")"; rc=$?
if [ -z "$out" ] && [ "$rc" -eq 0 ]; then echo "PASS: below threshold -> passthrough"; PASS=$((PASS+1)); else echo "FAIL: below threshold (rc=$rc)"; FAIL=$((FAIL+1)); fi

# 5. DEFAULT (no env) + headroom present -> COMPRESSES (proves it's on by default).
out="$(echo "$payload" | env PYTHONPATH="$mock" "$HOOK")"; rc=$?
if [ "$rc" -eq 0 ] && echo "$out" | grep -q '"updatedToolOutput"' && echo "$out" | grep -q 'COMPRESSED:'; then
  echo "PASS: default-on + headroom -> updatedToolOutput"; PASS=$((PASS+1))
else
  echo "FAIL: default-on happy path (rc=$rc, out=${out:0:80})"; FAIL=$((FAIL+1))
fi

rmtree "$mock"
echo "----"
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
