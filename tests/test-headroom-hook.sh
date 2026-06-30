#!/usr/bin/env bash
# Tests for Option D — bin/headroom-compress.py (the token-compression PostToolUse hook).
# Two tiers: Tier 1 = real headroom if importable; Tier 2 = pure-stdlib lite-crush
# (bin/lite_crush.py), always available. ENABLED by default; LOOBSTER_HEADROOM=0 disables
# both tiers, LOOBSTER_LITE_CRUSH=0 disables only Tier 2.
# Verifies: lite-crush compresses with NO headroom installed, headroom is preferred and
# its CompressResult object is handled, headroom failures fall back to lite-crush, kill
# switches, size threshold, and graceful passthrough.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$ROOT/bin/headroom-compress.py"
PASS=0
FAIL=0
TMP="$(mktemp -d)"
trap 'python3 -c "import shutil,sys; shutil.rmtree(sys.argv[1], ignore_errors=True)" "$TMP"' EXIT

# --- build payloads (python avoids shell newline-escaping headaches) ---
python3 - "$TMP" <<'PY'
import json, os, sys
tmp = sys.argv[1]
def w(name, output):
    open(os.path.join(tmp, name), "w").write(
        json.dumps({"tool_name": "Read", "tool_response": {"output": output}}))
w("dup.json", "repeated log line here\n" * 300)              # lite-crush CAN shrink
w("uniq.json", "\n".join("unique-line-%04d" % i for i in range(400)))  # lite-crush CANNOT
w("small.json", "tiny")                                       # below threshold
PY

# --- mock headroom modules on PYTHONPATH ---
mock="$TMP/mock"; mkdir -p "$mock"        # real-shape: compress() -> CompressResult object
cat > "$mock/headroom.py" <<'PY'
class CompressResult:
    def __init__(self, messages):
        self.messages = messages; self.tokens_saved = 0; self.compression_ratio = 1.0
def compress(messages, model=None):
    text = messages[-1]["content"] if isinstance(messages, list) else str(messages)
    return CompressResult([{"role": "user", "content": "HRCOMPRESSED:" + str(len(text))}])
PY
mockstr="$TMP/mockstr"; mkdir -p "$mockstr"   # back-compat: compress() -> plain str
cat > "$mockstr/headroom.py" <<'PY'
def compress(messages, model=None):
    text = messages[-1]["content"] if isinstance(messages, list) else str(messages)
    return "HRCOMPRESSED:" + str(len(text))
PY
mockraise="$TMP/mockraise"; mkdir -p "$mockraise"  # headroom present but throws
cat > "$mockraise/headroom.py" <<'PY'
def compress(messages, model=None):
    raise RuntimeError("boom")
PY

ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1"; FAIL=$((FAIL+1)); }

# expect_passthrough <name> <payload> [env...]
expect_passthrough(){
  local name="$1" pf="$TMP/$2"; shift 2
  local out rc; out="$(env "$@" "$HOOK" < "$pf")"; rc=$?
  if [ -z "$out" ] && [ "$rc" -eq 0 ]; then ok "$name"; else no "$name (rc=$rc out=${out:0:60})"; fi
}
# expect_compress <name> <payload> <needle> [env...]
expect_compress(){
  local name="$1" pf="$TMP/$2" needle="$3"; shift 3
  local out rc; out="$(env "$@" "$HOOK" < "$pf")"; rc=$?
  if [ "$rc" -eq 0 ] && echo "$out" | grep -q '"updatedToolOutput"' && echo "$out" | grep -q "$needle"; then
    ok "$name"; else no "$name (rc=$rc out=${out:0:90})"; fi
}

# 1. DEFAULT on, headroom ABSENT -> lite-crush compresses (works with nothing installed).
expect_compress "default-on + no headroom -> lite-crush" dup.json "loobster-crush"

# 2. lite-crush can't shrink the output -> passthrough.
expect_passthrough "lite-crush no gain -> passthrough" uniq.json

# 3. Below size threshold -> passthrough.
expect_passthrough "below threshold -> passthrough" small.json

# 4. Kill switch LOOBSTER_HEADROOM=0 -> passthrough even with headroom present.
expect_passthrough "LOOBSTER_HEADROOM=0 disables both tiers" dup.json LOOBSTER_HEADROOM=0 PYTHONPATH="$mock"

# 5. LOOBSTER_LITE_CRUSH=0 + headroom absent -> passthrough (Tier 2 off, Tier 1 unavailable).
expect_passthrough "LOOBSTER_LITE_CRUSH=0 + no headroom -> passthrough" dup.json LOOBSTER_LITE_CRUSH=0

# 6. Tier 1 preferred: real CompressResult object is handled (this is the bug-fix guard).
expect_compress "headroom CompressResult object -> used" dup.json "HRCOMPRESSED" PYTHONPATH="$mock"

# 7. Back-compat: headroom returning a plain string still works.
expect_compress "headroom str return -> used" dup.json "HRCOMPRESSED" PYTHONPATH="$mockstr"

# 8. Tier 1 throws -> graceful fall-through to Tier 2 lite-crush.
expect_compress "headroom raises -> lite-crush fallback" dup.json "loobster-crush" PYTHONPATH="$mockraise"

# 9. Malformed stdin -> passthrough.
out="$(echo 'not json' | "$HOOK")"; rc=$?
if [ -z "$out" ] && [ "$rc" -eq 0 ]; then ok "malformed stdin -> passthrough"; else no "malformed stdin (rc=$rc)"; fi

echo "----"
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
