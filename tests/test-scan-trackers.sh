#!/usr/bin/env bash
# Tests for bin/scan-trackers.py — detect third-party tracking/ads/analytics scripts.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCAN="$ROOT/bin/scan-trackers.py"
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

tmp="$(mktemp -d)"

# A page that loads Google Tag Manager + Meta Pixel.
cat > "$tmp/index.html" <<'EOF'
<!doctype html><html><head>
<script src="https://www.googletagmanager.com/gtag/js?id=G-ABCDE12345"></script>
<script>gtag('config','G-ABCDE12345');</script>
<script>!function(f,b){fbq('init','123');}(window);</script>
<script src="https://connect.facebook.net/en_US/fbevents.js"></script>
</head><body>hi</body></html>
EOF

# A clean component (no trackers).
cat > "$tmp/Clean.tsx" <<'EOF'
export function Clean() { return <div>just UI, nothing external here</div>; }
EOF

# 1. default (report) exits 0 and finds the trackers.
out="$(python3 "$SCAN" "$tmp")"; rc=$?
{ [ "$rc" = 0 ] && echo "$out" | grep -q "Google Tag Manager" && echo "$out" | grep -q "Meta / Facebook Pixel"; } \
  && ok "detects GTM + Meta Pixel" || no "detection" "rc=$rc out=$out"

# 2. --strict exits 1 when trackers are present.
python3 "$SCAN" "$tmp" --strict >/dev/null 2>&1; rc=$?
[ "$rc" = 1 ] && ok "--strict exits 1 on findings" || no "strict exit" "rc=$rc"

# 3. clean-only tree -> no findings, exit 0 even with --strict.
clean="$(mktemp -d)"; cp "$tmp/Clean.tsx" "$clean/"
out="$(python3 "$SCAN" "$clean" --strict)"; rc=$?
{ [ "$rc" = 0 ] && echo "$out" | grep -qi "no third-party trackers"; } && ok "clean tree -> exit 0, no findings" || no "clean" "rc=$rc out=$out"
rm -rf "$clean"

# 4. --json emits valid machine-readable output including a finding.
out="$(python3 "$SCAN" "$tmp" --json)"
echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); assert any(x['tracker']=='Meta / Facebook Pixel' for x in d)" 2>/dev/null \
  && ok "--json valid + includes a finding" || no "json" "$out"

rm -rf "$tmp"
echo "----"; echo "$PASS passed, $FAIL failed"; [ "$FAIL" -eq 0 ]
