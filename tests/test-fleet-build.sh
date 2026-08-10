#!/usr/bin/env bash
# Tests for bin/fleet-build.py (cross-branch fleet dashboard for GitHub Pages).
# Verifies: aggregates markers from MULTIPLE branches (the pr-lane case); the
# --days window prunes stale branches but keeps the default branch; data.json +
# self-contained index.html with embedded data and the edit-back API wiring;
# --out is required (no cwd pollution); non-repo and --help behave.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLEET="$ROOT/bin/fleet-build.py"
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }
rmtree(){ python3 -c "import shutil,sys;shutil.rmtree(sys.argv[1],ignore_errors=True)" "$1"; }
G(){ git -C "$1" -c user.email=t@t -c user.name=t "${@:2}" >/dev/null 2>&1; }

mkrepo(){ # main with one done loop + a signal; feature branch with an active pr-lane loop
  local d; d="$(mktemp -d)"
  G "$d" init -b main
  mkdir -p "$d/plans/loop" "$d/signals"
  printf -- '---\nstatus: done\ngoalId: shipped\ngoal: Old goal\ncycle: 9\n---\n' > "$d/plans/loop/shipped.md"
  printf -- '---\nstatus: new\ntype: friction\nauthor: ana\n---\nusers ask about export\n' > "$d/signals/2026-08-01-ana-export.md"
  G "$d" add -A; G "$d" commit -m main
  G "$d" checkout -b feat/loop-work
  printf -- '---\nstatus: active\ngoalId: cov\ngoal: Raise coverage\ncycle: 3\nmaxCycles: 10\ndeliveryMode: pr-lane\nbacklogOpen: 4\nbacklogDone: 2\n---\n' > "$d/plans/loop/cov.md"
  G "$d" add -A; G "$d" commit -m feat
  G "$d" checkout main
  echo "$d"; }

# 1. Aggregates loops from BOTH branches; active first; repo flag lands in data.json.
d="$(mkrepo)"; out="$d/_site"
res="$(python3 "$FLEET" --root "$d" --out "$out" --repo acme/widgets)"; rc=$?
{ [ "$rc" = 0 ] && [ -f "$out/data.json" ] && [ -f "$out/index.html" ] \
  && python3 - "$out/data.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
loops = d["loops"]
assert d["repo"] == "acme/widgets", d["repo"]
assert [l["goalId"] for l in loops] == ["cov", "shipped"], loops
assert loops[0]["branch"] == "feat/loop-work" and loops[0]["deliveryMode"] == "pr-lane"
assert loops[1]["branch"] == "main", "inherited marker must dedup to the default branch"
assert d["signals"]["counts"].get("new") == 1
EOF
} && ok "aggregates across branches (active first, inherited markers deduped)" \
  || no "cross-branch aggregate" "rc=$rc res=$res"

# 2. index.html is self-contained: embedded data, edit-back wiring, no external fetches.
{ grep -q 'fleet-data' "$out/index.html" && grep -q 'Raise coverage' "$out/index.html" \
  && grep -q 'api.github.com' "$out/index.html" && grep -q 'setStatus' "$out/index.html" \
  && ! grep -qi 'src="http' "$out/index.html"; } \
  && ok "self-contained editable index.html" || no "index.html" "missing pieces"

# 3. --days 0 prunes the (old-enough) feature branch... but default branch always stays.
#    All commits are 'now', so instead verify the default branch survives an empty window
#    by checking data.json still contains the main-branch loop with --days 0.
res="$(python3 "$FLEET" --root "$d" --out "$out" --days 0 --repo acme/widgets)"
python3 - "$out/data.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
assert "main" in d["branchesScanned"], d["branchesScanned"]
assert any(l["goalId"] == "shipped" for l in d["loops"])
EOF
[ $? = 0 ] && ok "default branch always included" || no "--days window" "$res"
rmtree "$d"

# 4. --out is required (no silent cwd pollution).
d="$(mkrepo)"
python3 "$FLEET" --root "$d" >/dev/null 2>&1; [ $? = 2 ] && ok "--out required" || no "--out required" "rc=$?"
rmtree "$d"

# 5. Not a git repo -> exit 2; --help -> exit 0.
e="$(mktemp -d)"
python3 "$FLEET" --root "$e" --out "$e/x" >/dev/null 2>&1; [ $? = 2 ] && ok "non-repo -> exit 2" || no "non-repo" "rc=$?"
rmtree "$e"
python3 "$FLEET" --help | grep -q 'fleet-build' && ok "--help" || no "--help" "no usage"

echo "----"; echo "$PASS passed, $FAIL failed"; [ "$FAIL" -eq 0 ]
