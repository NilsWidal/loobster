#!/usr/bin/env bash
# Unit tests for bin/lite_crush.py — the pure-stdlib, deterministic, dependency-free
# Tier 2 crusher. Verifies lossless JSON minify, marked lossy collapses, no-op safety,
# trailing-whitespace stripping, and determinism.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

python3 - "$ROOT/bin" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1])
from lite_crush import crush

fails = 0
def check(name, cond):
    global fails
    print(("PASS: " if cond else "FAIL: ") + name)
    if not cond:
        fails += 1

# JSON minify: smaller AND lossless (data preserved).
pretty = json.dumps({"a": 1, "b": [1, 2, 3], "c": {"d": "e" * 50}}, indent=2)
out = crush(pretty)
check("json minify is shorter", len(out) < len(pretty))
check("json minify is lossless", json.loads(out) == json.loads(pretty))

# Repeated lines collapse and are explicitly marked.
dup = "same line\n" * 50
out = crush(dup)
check("dup run collapses", len(out) < len(dup))
check("dup run is marked", "loobster-crush" in out)

# Unique lines with nothing to gain -> returned unchanged.
uniq = "\n".join("u%03d" % i for i in range(50))
check("incompressible is unchanged", crush(uniq) == uniq)

# Very long single line -> clamped and marked.
out = crush("x" * 5000)
check("long line clamped", len(out) < 5000 and "loobster-crush" in out)

# Trailing whitespace stripped; final newline preserved.
check("trailing whitespace stripped", crush("abc   \ndef\t\n") == "abc\ndef\n")

# Determinism + safe no-ops.
check("deterministic", crush(dup) == crush(dup))
check("empty string safe", crush("") == "")
check("whitespace-only safe", crush("   ") == "   ")

print("----")
print("0 failed" if fails == 0 else f"{fails} failed")
sys.exit(1 if fails else 0)
PY
