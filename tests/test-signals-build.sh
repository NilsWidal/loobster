#!/usr/bin/env bash
# Tests for bin/signals-build.py — parse signals/*.md into data.js/data.json/INDEX.md,
# skip malformed files, and flag PHI-shaped content.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/bin/signals-build.py"
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1"; FAIL=$((FAIL+1)); }

tmp="$(mktemp -d)"; sig="$tmp/signals"; mkdir -p "$sig"

# Two valid signals
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
5 users this week asked how to export.
EOF

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

# PHI-shaped: structurally valid but body contains a PHI keyword (DOB)
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

echo "=== run (non-strict) ==="
out="$(python3 "$BUILD" "$sig" 2>&1)"; rc=$?
echo "$out"

[ "$rc" -eq 0 ] && ok "non-strict exits 0" || no "non-strict exit ($rc)"
echo "$out" | grep -q "skip (malformed): oops-malformed.md" && ok "malformed skipped" || no "malformed not skipped"
echo "$out" | grep -q "PHI-shaped.*sam-phi" && ok "PHI-shaped flagged" || no "PHI not flagged"

# 3 structurally-valid signals in output (2 clean + 1 phi); malformed excluded
n=$(python3 -c "import json;print(len(json.load(open('$sig/data.json'))))")
[ "$n" -eq 3 ] && ok "data.json has 3 valid signals" || no "data.json count=$n (want 3)"
grep -q "window.SIGNALS" "$sig/data.js" && ok "data.js defines window.SIGNALS" || no "data.js missing global"
grep -q "Export is too hidden" "$sig/INDEX.md" && ok "INDEX.md lists active signal" || no "INDEX.md missing active"
# archived signal excluded from INDEX active view
grep -q "lovable-alternative" "$sig/INDEX.md" && no "archived leaked into INDEX active" || ok "archived excluded from INDEX active"

echo "=== run (--strict) -> expect exit 1 (malformed + PHI present) ==="
python3 "$BUILD" "$sig" --strict >/dev/null 2>&1; rc=$?
[ "$rc" -eq 1 ] && ok "--strict exits 1 on malformed/PHI" || no "--strict exit ($rc, want 1)"

rm -rf "$tmp"
echo "----"; echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
