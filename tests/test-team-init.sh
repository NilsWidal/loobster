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

mkfakegh(){ # $1 bindir  $2 visibility  $3 plan(default free)  $4 readback-public override
  local pub="${4:-}"                              # bake the live read-back exposure
  if [ -z "$pub" ]; then
    pub=true; [ "$2" = "PRIVATE" ] && case "${3:-free}" in *enterprise*) pub=false;; esac
  fi
  cat > "$1/gh" <<EOF
#!/usr/bin/env bash
echo "\$*" >> "$1/gh.log"
case "\$*" in
  "auth status") exit 0 ;;
  *nameWithOwner*) echo "acme/widgets" ;;
  *visibility*) echo "$2" ;;
  *defaultBranchRef*) echo "main" ;;
  *plan.name*) echo "${3:-free}" ;;                          # plan query
  *"/pages"*html_url*)                                        # live read-back
      printf '%s\t%s\n' "https://acme.github.io/widgets/" "$pub" ;;
  *"-X DELETE"*"/pages"*)                                     # rollback
      [ -f "$1/delete_fails" ] && exit 1 || exit 0 ;;
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

# 7. PRIVATE repo on GitHub Enterprise Cloud: Pages is genuinely private, so it
#    enables with NO --public-ok; --protect-main sets branch protection; reports private.
d="$(mkrepo)"; fake="$(mktemp -d)"; mkfakegh "$fake" PRIVATE enterprise
out="$(PATH="$fake:$PATH" bash "$INIT" --repo "$d" --protect-main 2>&1)"; rc=$?
{ [ "$rc" = 0 ] && grep -q "repos/acme/widgets/pages" "$fake/gh.log" \
  && grep -q "branches/main/protection" "$fake/gh.log" \
  && echo "$out" | grep -q "private (Enterprise)"; } \
  && ok "private+Enterprise -> Pages (private) + protection" \
  || no "enterprise private path" "rc=$rc out=$out"
rmtree "$d"; rmtree "$fake"

# 7b. PRIVATE repo NOT on Enterprise: GitHub serves Pages publicly -> REFUSE (exit 3),
#     no pages API call. This is the core fix (was silently published before).
d="$(mkrepo)"; fake="$(mktemp -d)"; mkfakegh "$fake" PRIVATE free
out="$(PATH="$fake:$PATH" bash "$INIT" --repo "$d" 2>&1)"; rc=$?
{ [ "$rc" = 3 ] && ! grep -q "/pages" "$fake/gh.log" 2>/dev/null \
  && echo "$out" | grep -q "WORLD-READABLE"; } \
  && ok "private+non-Enterprise -> refused (exit 3, not published)" \
  || no "private public-pages refusal" "rc=$rc out=$out"

# 7c. Same, with --public-ok: enables and reports the board as PUBLIC.
rm -f "$fake/gh.log"
out="$(PATH="$fake:$PATH" bash "$INIT" --repo "$d" --public-ok --force 2>&1)"; rc=$?
{ [ "$rc" = 0 ] && grep -q "repos/acme/widgets/pages" "$fake/gh.log" \
  && echo "$out" | grep -qi "PUBLIC"; } \
  && ok "private+non-Enterprise + --public-ok -> enabled, warned PUBLIC" \
  || no "private public-ok" "rc=$rc out=$out"
rmtree "$d"; rmtree "$fake"

# 7d. PRIVATE + Enterprise, but the org policy actually serves Pages PUBLICLY
#     (read-back says public): with no --public-ok, roll back (DELETE) and exit 3.
d="$(mkrepo)"; fake="$(mktemp -d)"; mkfakegh "$fake" PRIVATE enterprise true
out="$(PATH="$fake:$PATH" bash "$INIT" --repo "$d" 2>&1)"; rc=$?
{ [ "$rc" = 3 ] && grep -q "api -X DELETE repos/acme/widgets/pages" "$fake/gh.log" \
  && echo "$out" | grep -q "DISABLED again"; } \
  && ok "enterprise+private but served public -> rolled back (exit 3)" \
  || no "public rollback" "rc=$rc out=$out log=$(cat "$fake/gh.log" 2>/dev/null)"

# 7e. Same, WITH --public-ok: the human accepted it, so it stays published.
rm -f "$fake/gh.log"
out="$(PATH="$fake:$PATH" bash "$INIT" --repo "$d" --public-ok --force 2>&1)"; rc=$?
{ [ "$rc" = 0 ] && ! grep -q "api -X DELETE" "$fake/gh.log" \
  && echo "$out" | grep -qi "accepted via --public-ok"; } \
  && ok "enterprise+private served public + --public-ok -> kept" \
  || no "public accepted" "rc=$rc out=$out"
rmtree "$d"; rmtree "$fake"

# 7f. Rollback DELETE itself fails -> do NOT claim it was disabled; warn STILL PUBLIC.
d="$(mkrepo)"; fake="$(mktemp -d)"; mkfakegh "$fake" PRIVATE enterprise true
touch "$fake/delete_fails"
out="$(PATH="$fake:$PATH" bash "$INIT" --repo "$d" 2>&1)"; rc=$?
{ [ "$rc" = 3 ] && echo "$out" | grep -q "STILL PUBLIC" \
  && ! echo "$out" | grep -q "Nothing is left published"; } \
  && ok "failed rollback -> honest STILL PUBLIC warning (exit 3)" \
  || no "rollback failure honesty" "rc=$rc out=$out"
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
