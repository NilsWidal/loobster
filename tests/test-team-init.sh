#!/usr/bin/env bash
# Tests for bin/team-init.sh (/team-setup — one-command GitHub team wiring).
# Verifies: vendors the workflow + the scripts Actions runs (version-stamped,
# still executable), scaffolds signals/ + plans/loop/, idempotent without
# --force, refuses Pages on a public repo (exit 3) unless --public-ok, enables
# Pages + protection via gh on a private repo, --dry-run writes nothing,
# warns on a leftover signals-pages.yml, non-repo and --help behave.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INIT="$ROOT/bin/team-init.sh"
PASS=0; FAIL=0
ok(){ echo "PASS: $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }
rmtree(){ python3 -c "import shutil,sys;shutil.rmtree(sys.argv[1],ignore_errors=True)" "$1"; }
G(){ git -C "$1" -c user.email=t@t -c user.name=t "${@:2}" >/dev/null 2>&1; }

mkrepo(){ local d; d="$(mktemp -d)"; G "$d" init -b main; echo x > "$d/x"; G "$d" add -A; G "$d" commit -m init; echo "$d"; }

mkfakegh(){ # $1 bindir  $2 visibility — logs every call to $1/gh.log
  cat > "$1/gh" <<EOF
#!/usr/bin/env bash
echo "\$*" >> "$1/gh.log"
case "\$*" in
  "auth status") exit 0 ;;
  *nameWithOwner*) echo "acme/widgets" ;;
  *visibility*) echo "$2" ;;
  *defaultBranchRef*) echo "main" ;;
esac
exit 0
EOF
  chmod +x "$1/gh"
}

# 1. Vendors everything + scaffolds, stamped with the plugin version, still runnable.
d="$(mkrepo)"
out="$(bash "$INIT" --repo "$d" --no-pages 2>&1)"; rc=$?
{ [ "$rc" = 0 ] \
  && [ -f "$d/.github/workflows/fleet-pages.yml" ] && [ -f "$d/bin/fleet-build.py" ] \
  && [ -f "$d/bin/signals-build.py" ] && [ -f "$d/templates/signals-dashboard.html" ] \
  && [ -f "$d/signals/README.md" ] && [ -f "$d/plans/loop/.gitkeep" ] \
  && head -1 "$d/.github/workflows/fleet-pages.yml" | grep -q "vendored from loobster" \
  && sed -n 2p "$d/bin/fleet-build.py" | grep -q "vendored from loobster" \
  && head -1 "$d/bin/fleet-build.py" | grep -q '^#!' \
  && head -1 "$d/templates/signals-dashboard.html" | grep -q '^<!-- vendored' \
  && [ -x "$d/bin/fleet-build.py" ]; } \
  && ok "vendors + scaffolds, version-stamped, shebang preserved" \
  || no "vendor" "rc=$rc out=$out"

# 2. Vendored fleet-build.py still runs (the stamp didn't break it).
python3 "$d/bin/fleet-build.py" --help 2>/dev/null | grep -q fleet-build \
  && ok "vendored fleet-build.py runs" || no "vendored script broken" "--help failed"

# 3. Idempotent: a re-run without --force leaves local edits alone; --force refreshes.
echo "# local edit" >> "$d/bin/fleet-build.py"
out="$(bash "$INIT" --repo "$d" --no-pages 2>&1)"
grep -q "local edit" "$d/bin/fleet-build.py" && echo "$out" | grep -q "skip" \
  && ok "re-run skips existing files" || no "idempotency" "$out"
bash "$INIT" --repo "$d" --no-pages --force >/dev/null 2>&1
! grep -q "local edit" "$d/bin/fleet-build.py" \
  && ok "--force refreshes vendored files" || no "--force" "edit survived"

# 4. Leftover signals-pages.yml -> replacement warning (one Pages site per repo).
mkdir -p "$d/.github/workflows"; touch "$d/.github/workflows/signals-pages.yml"
out="$(bash "$INIT" --repo "$d" --no-pages 2>&1)"
echo "$out" | grep -q "replaces it" && ok "warns on signals-pages.yml" || no "conflict warn" "$out"
rmtree "$d"

# 5. PUBLIC repo: refuses Pages with exit 3, never calls the pages API.
d="$(mkrepo)"; fake="$(mktemp -d)"; mkfakegh "$fake" PUBLIC
out="$(PATH="$fake:$PATH" bash "$INIT" --repo "$d" 2>&1)"; rc=$?
{ [ "$rc" = 3 ] && ! grep -q "pages" "$fake/gh.log" 2>/dev/null \
  && echo "$out" | grep -q "REFUSING"; } \
  && ok "public repo -> compliance refusal (exit 3, no API call)" \
  || no "public refusal" "rc=$rc out=$out"

# 6. PUBLIC + --public-ok: explicit override enables Pages.
rm -f "$fake/gh.log"
PATH="$fake:$PATH" bash "$INIT" --repo "$d" --public-ok --force >/dev/null 2>&1; rc=$?
{ [ "$rc" = 0 ] && grep -q "api -X POST repos/acme/widgets/pages" "$fake/gh.log"; } \
  && ok "--public-ok overrides (pages API called)" || no "--public-ok" "rc=$rc log=$(cat "$fake/gh.log" 2>/dev/null)"
rmtree "$d"; rmtree "$fake"

# 7. PRIVATE repo: enables Pages; --protect-main sets branch protection.
d="$(mkrepo)"; fake="$(mktemp -d)"; mkfakegh "$fake" PRIVATE
PATH="$fake:$PATH" bash "$INIT" --repo "$d" --protect-main >/dev/null 2>&1; rc=$?
{ [ "$rc" = 0 ] && grep -q "repos/acme/widgets/pages" "$fake/gh.log" \
  && grep -q "branches/main/protection" "$fake/gh.log"; } \
  && ok "private repo -> Pages + branch protection via gh" \
  || no "private path" "rc=$rc log=$(cat "$fake/gh.log" 2>/dev/null)"
rmtree "$d"; rmtree "$fake"

# 8. --dry-run writes nothing.
d="$(mkrepo)"
out="$(bash "$INIT" --repo "$d" --dry-run 2>&1)"; rc=$?
{ [ "$rc" = 0 ] && [ ! -e "$d/.github/workflows/fleet-pages.yml" ] \
  && [ ! -e "$d/signals" ] && echo "$out" | grep -q "would"; } \
  && ok "--dry-run plans without writing" || no "--dry-run" "rc=$rc"
rmtree "$d"

# 9. Not a git repo -> exit 2; --help -> exit 0; unknown flag -> exit 2.
e="$(mktemp -d)"
bash "$INIT" --repo "$e" >/dev/null 2>&1; [ $? = 2 ] && ok "non-repo -> exit 2" || no "non-repo" "rc=$?"
rmtree "$e"
bash "$INIT" --help | grep -q team-init && ok "--help" || no "--help" "no usage"
bash "$INIT" --bogus >/dev/null 2>&1; [ $? = 2 ] && ok "unknown flag -> exit 2" || no "unknown flag" "rc=$?"

echo "----"; echo "$PASS passed, $FAIL failed"; [ "$FAIL" -eq 0 ]
