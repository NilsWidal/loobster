#!/usr/bin/env bash
# Tests for bin/signals-build.py — parse signals/*.md into data.js/data.json/INDEX.md,
# skip malformed files, flag + quarantine PHI-shaped content, and never pollute the cwd.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/bin/signals-build.py"
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1"; FAIL=$((FAIL+1)); }

tmp="$(mktemp -d)"; sig="$tmp/signals"; mkdir -p "$sig"

# Valid signal (active, body starts with a bullet — exercises the M08 fix)
cat > "$sig/2026-06-21-nils-export-too-hidden.md" <<'EOF'
---
id: 2026-06-21-nils-export-too-hidden
author: nils
source: support-loop
ts: 2026-06-21T14:30:00Z
type: friction
confidence: 0.8
relevance: [product, onboarding]
status: new
title: Export is too hidden
---
- 5 users this week asked how to export.
- The action is 3 clicks deep.
EOF

# Valid signal (archived)
cat > "$sig/2026-06-21-amy-cpc-good.md" <<'EOF'
---
id: 2026-06-21-amy-cpc-good
author: amy
source: ads-loop
ts: 2026-06-21T09:00:00Z
type: opportunity
confidence: 1.0
relevance: [ads]
status: archived
title: lovable-alternative CPC is good
---
CPC trending well on that landing page.
EOF

# Malformed: no frontmatter
echo "just a note, no frontmatter" > "$sig/oops-malformed.md"

# PHI-shaped (DOB keyword)
cat > "$sig/2026-06-21-sam-phi.md" <<'EOF'
---
id: 2026-06-21-sam-phi
author: sam
source: support-loop
ts: 2026-06-21T10:00:00Z
type: fact
confidence: 0.5
relevance: [support]
status: new
title: ticket references a DOB field
---
A ticket body included a DOB which should never be in a signal.
EOF

# PHI recall: a named patient in free text (lowercase) + a record number (H06)
cat > "$sig/2026-06-21-recall-name.md" <<'EOF'
---
id: 2026-06-21-recall-name
author: sam
source: support-loop
ts: 2026-06-21T11:00:00Z
type: fact
confidence: 0.5
relevance: [support]
status: new
title: login issue
---
patient jane keeps failing login; her record number is 884213.
EOF

echo "=== run (non-strict, default quarantine) ==="
out="$(python3 "$BUILD" "$sig" 2>&1)"; rc=$?
echo "$out"

[ "$rc" -eq 0 ] && ok "non-strict exits 0" || no "non-strict exit ($rc)"
echo "$out" | grep -q "skip (malformed): oops-malformed.md" && ok "malformed skipped" || no "malformed not skipped"
echo "$out" | grep -q "PHI-shaped.*sam-phi" && ok "PHI (DOB) flagged" || no "DOB not flagged"
echo "$out" | grep -qi "QUARANTINED" && ok "PHI quarantined by default" || no "no quarantine notice"
echo "$out" | grep -q "recall-name" && ok "named patient + record number flagged (recall)" || no "recall PHI not flagged"

# 2 clean signals in output (export + amy); PHI signals quarantined, malformed excluded
n=$(python3 -c "import json;print(len(json.load(open('$sig/data.json'))))")
[ "$n" -eq 2 ] && ok "data.json has 2 valid signals (PHI quarantined)" || no "data.json count=$n (want 2)"
grep -q "sam-phi" "$sig/data.json" && no "PHI signal leaked into data.json" || ok "PHI signal kept out of data.json"
grep -q "window.SIGNALS" "$sig/data.js" && ok "data.js defines window.SIGNALS" || no "data.js missing global"
grep -q "Export is too hidden" "$sig/INDEX.md" && ok "INDEX.md lists active signal" || no "INDEX.md missing active"
grep -q "5 users this week" "$sig/data.json" && ok "list-led body keeps first bullet (M08)" || no "first bullet eaten"
grep -q "lovable-alternative" "$sig/INDEX.md" && no "archived leaked into INDEX active" || ok "archived excluded from INDEX active"

echo "=== run (--allow-flagged) ==="
python3 "$BUILD" "$sig" --allow-flagged >/dev/null 2>&1
n=$(python3 -c "import json;print(len(json.load(open('$sig/data.json'))))")
[ "$n" -eq 4 ] && ok "--allow-flagged includes PHI signals (4 total)" || no "--allow-flagged count=$n (want 4)"

echo "=== run (--strict) -> expect exit 1 (malformed + PHI present) ==="
python3 "$BUILD" "$sig" --strict >/dev/null 2>&1; rc=$?
[ "$rc" -eq 1 ] && ok "--strict exits 1 on malformed/PHI" || no "--strict exit ($rc, want 1)"

echo "=== no signals dir -> must NOT write into cwd (H04) ==="
cwd="$(mktemp -d)"; ( cd "$cwd" && python3 "$BUILD" "nope" >/dev/null 2>&1 ); rc=$?
[ "$rc" -eq 0 ] && ok "missing dir exits 0" || no "missing dir exit ($rc)"
if [ -e "$cwd/data.json" ] || [ -e "$cwd/data.js" ] || [ -e "$cwd/INDEX.md" ]; then
  no "missing dir polluted cwd"
else
  ok "missing dir wrote nothing to cwd"
fi
rm -rf "$cwd"

rm -rf "$tmp"
echo "----"; echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
