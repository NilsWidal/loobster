#!/usr/bin/env bash
# Tests for Option D — bin/headroom-compress.py (the optional headroom PostToolUse hook).
# Verifies: default-OFF, graceful passthrough on every failure path, the size
# threshold, and the happy path (emits updatedToolOutput) using a mock headroom module.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$ROOT/bin/headroom-compress.py"
PASS=0
FAIL=0

big="$(python3 -c "print('x'*5000)")"
payload="{\"tool_name\":\"Read\",\"tool_response\":{\"output\":\"$big\"}}"

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

# 1. Default OFF -> passthrough (no REPPIT_HEADROOM).
assert_empty "default off -> passthrough"

# 2. Enabled but headroom not importable -> passthrough.
assert_empty "enabled + headroom absent -> passthrough" REPPIT_HEADROOM=1

# 3. Malformed stdin -> passthrough.
out="$(echo 'not json' | REPPIT_HEADROOM=1 "$HOOK")"; rc=$?
if [ -z "$out" ] && [ "$rc" -eq 0 ]; then echo "PASS: malformed stdin -> passthrough"; PASS=$((PASS+1)); else echo "FAIL: malformed stdin (rc=$rc)"; FAIL=$((FAIL+1)); fi

# 4. Output below size threshold -> passthrough.
small='{"tool_name":"Read","tool_response":{"output":"tiny"}}'
out="$(echo "$small" | REPPIT_HEADROOM=1 "$HOOK")"; rc=$?
if [ -z "$out" ] && [ "$rc" -eq 0 ]; then echo "PASS: below threshold -> passthrough"; PASS=$((PASS+1)); else echo "FAIL: below threshold (rc=$rc)"; FAIL=$((FAIL+1)); fi

# 5. Happy path: enabled + a mock headroom module that compresses -> emits updatedToolOutput.
tmp="$(mktemp -d)"
cat > "$tmp/headroom.py" <<'PY'
def compress(text, model=None):
    return "COMPRESSED:" + str(len(text))
PY
out="$(echo "$payload" | env REPPIT_HEADROOM=1 PYTHONPATH="$tmp" "$HOOK")"; rc=$?
if [ "$rc" -eq 0 ] && echo "$out" | grep -q '"updatedToolOutput"' && echo "$out" | grep -q 'COMPRESSED:'; then
  echo "PASS: enabled + mock headroom -> updatedToolOutput"; PASS=$((PASS+1))
else
  echo "FAIL: happy path (rc=$rc, out=${out:0:80})"; FAIL=$((FAIL+1))
fi
rm -rf "$tmp"

echo "----"
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
