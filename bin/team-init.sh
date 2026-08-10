#!/usr/bin/env bash
# team-init.sh — make a repo team-ready on GitHub in one command (/team-setup).
#
# GitHub is the server: Actions is the runtime, Pages is the UI, git is the
# only data plane. This script does the one-time wiring for a TARGET repo:
#
#   1. Vendors the fleet dashboard workflow AND the scripts it runs.
#      Actions executes `python3 bin/fleet-build.py` from the repo checkout,
#      where the plugin install directory does not exist — so the copies are
#      load-bearing, not convenience:
#        templates/fleet-pages.yml        -> .github/workflows/fleet-pages.yml
#        bin/fleet-build.py               -> bin/fleet-build.py
#        bin/signals-build.py             -> bin/signals-build.py
#        templates/signals-dashboard.html -> templates/signals-dashboard.html
#      Each copy is stamped "vendored from loobster vX.Y.Z"; re-run with
#      --force after a plugin upgrade to refresh them.
#   2. Scaffolds signals/README.md and plans/loop/ (the marker directory).
#   3. Enables GitHub Pages (Source: GitHub Actions) via `gh api` — after a
#      visibility check: on a non-private repo it REFUSES (exit 3) unless
#      --public-ok, because Pages there serves your business state to the
#      world. See compliance/org-controls-audit.md.
#   4. Optionally (--protect-main) requires one approving PR review to land
#      on the default branch.
#
# Exit: 0 ok · 2 usage / not a repo / missing source · 3 compliance refusal
set -u

usage(){ cat <<'EOF'
team-init.sh — make a repo team-ready on GitHub in one command (/team-setup)

  bash bin/team-init.sh [--repo <dir>] [flags]

  --repo <dir>         target repo (default: current directory)
  --public-ok          allow enabling Pages on a non-private repo (an explicit
                       human decision — the board becomes world-readable)
  --no-pages           vendor + scaffold only; skip the gh/Pages step
  --protect-main       require 1 approving PR review on the default branch
  --force              refresh vendored files (after a plugin upgrade)
  --dry-run            print the plan, write nothing, call nothing
  --plugin-root <dir>  vendor from here (default: this script's parent dir)

Exit: 0 ok · 2 usage/not-a-repo/missing-source · 3 compliance refusal
EOF
}

REPO="$(pwd)"; PUBLIC_OK=0; NO_PAGES=0; PROTECT=0; FORCE=0; DRY=0
PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
while [ $# -gt 0 ]; do case "$1" in
  --repo)         REPO="${2:?--repo needs a dir}"; shift 2;;
  --plugin-root)  PLUGIN_ROOT="${2:?--plugin-root needs a dir}"; shift 2;;
  --public-ok)    PUBLIC_OK=1; shift;;
  --no-pages)     NO_PAGES=1; shift;;
  --protect-main) PROTECT=1; shift;;
  --force)        FORCE=1; shift;;
  --dry-run)      DRY=1; shift;;
  -h|--help)      usage; exit 0;;
  *) echo "unknown flag: $1" >&2; usage >&2; exit 2;;
esac; done

[ -d "$REPO" ] || { echo "not a directory: $REPO" >&2; exit 2; }
REPO="$(cd "$REPO" && pwd)"
git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repo: $REPO" >&2; exit 2; }

VERSION="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' \
  "$PLUGIN_ROOT/.claude-plugin/plugin.json" 2>/dev/null || echo unknown)"
STAMP="vendored from loobster v$VERSION — re-run /team-setup with --force to update"
ERRS=0

echo "loobster team-init (plugin v$VERSION) -> $REPO"

vendor(){ # $1 src-rel-to-plugin  $2 dst-rel-to-repo  $3 comment style: hash|html
  local src="$PLUGIN_ROOT/$1" dst="$REPO/$2"
  [ -f "$src" ] || { echo "  MISSING in plugin: $1" >&2; ERRS=$((ERRS+1)); return; }
  if [ -e "$dst" ] && [ "$FORCE" != 1 ]; then echo "  skip   $2 (exists; --force to refresh)"; return; fi
  if [ "$DRY" = 1 ]; then echo "  would  vendor $2"; return; fi
  python3 - "$src" "$dst" "$3" "$STAMP" <<'PY'
import sys, pathlib
src, dst, style, stamp = sys.argv[1:5]
text = pathlib.Path(src).read_text(encoding="utf-8")
line = {"hash": "# %s\n" % stamp, "html": "<!-- %s -->\n" % stamp}[style]
if text.startswith("#!"):                      # keep the shebang on line 1
    head, _, rest = text.partition("\n")
    text = head + "\n" + line + rest
else:
    text = line + text
p = pathlib.Path(dst)
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(text, encoding="utf-8")
PY
  case "$dst" in *.py|*.sh) chmod +x "$dst";; esac
  echo "  vendor $2 (loobster v$VERSION)"
}

scaffold(){ # $1 dst-rel  $2 content
  local dst="$REPO/$1"
  if [ -e "$dst" ]; then echo "  skip   $1 (exists)"; return; fi
  if [ "$DRY" = 1 ]; then echo "  would  create $1"; return; fi
  mkdir -p "$(dirname "$dst")"
  printf '%s' "$2" > "$dst"
  echo "  create $1"
}

echo "Vendoring (Actions runs these from the repo checkout, not the plugin):"
vendor templates/fleet-pages.yml        .github/workflows/fleet-pages.yml hash
vendor bin/fleet-build.py               bin/fleet-build.py                hash
vendor bin/signals-build.py             bin/signals-build.py              hash
vendor templates/signals-dashboard.html templates/signals-dashboard.html  html

echo "Scaffolding:"
scaffold signals/README.md "# Signals hub

One signal per file: \`<YYYY-MM-DD>-<author>-<slug>.md\` (frontmatter + 1-line body).
Emit/consume with /signals. Load-bearing rule: **non-PHI summaries only**.
"
scaffold plans/loop/.gitkeep ""

if [ -f "$REPO/.github/workflows/signals-pages.yml" ]; then
  echo "WARN: .github/workflows/signals-pages.yml exists — fleet-pages.yml replaces it" >&2
  echo "      (one Pages site per repo; the fleet board serves signals at /signals/)." >&2
  echo "      Remove signals-pages.yml in the same PR." >&2
fi

[ "$ERRS" = 0 ] || { echo "aborting: $ERRS source file(s) missing under $PLUGIN_ROOT" >&2; exit 2; }

# ---- GitHub side (Pages, optional branch protection) ------------------------
MANUAL_PAGES="enable manually: repo Settings -> Pages -> Source: GitHub Actions"
NWO=""; GH_READY=0
if [ "$DRY" = 1 ]; then
  [ "$NO_PAGES" = 1 ] || echo "Pages: would check repo visibility, then enable via gh api (build_type=github_actions)"
  [ "$PROTECT" = 0 ] || echo "Protection: would require 1 approving PR review on the default branch"
elif [ "$NO_PAGES" = 1 ] && [ "$PROTECT" = 0 ]; then
  echo "Pages: skipped (--no-pages); $MANUAL_PAGES"
elif ! command -v gh >/dev/null 2>&1; then
  echo "Pages: gh CLI not found; $MANUAL_PAGES"
elif ! gh auth status >/dev/null 2>&1; then
  echo "Pages: gh is not authenticated (run: gh auth login); $MANUAL_PAGES"
else
  NWO="$( (cd "$REPO" && gh repo view --json nameWithOwner -q .nameWithOwner) 2>/dev/null )"
  if [ -z "$NWO" ]; then
    echo "Pages: cannot resolve a GitHub repo (no remote yet?); push first, then $MANUAL_PAGES"
  else
    GH_READY=1
  fi
fi

if [ "$GH_READY" = 1 ] && [ "$NO_PAGES" != 1 ]; then
  VIS="$( (cd "$REPO" && gh repo view --json visibility -q .visibility) 2>/dev/null | tr '[:upper:]' '[:lower:]' )"
  if [ "$VIS" != "private" ] && [ "$PUBLIC_OK" != 1 ]; then
    cat >&2 <<EOF
REFUSING to enable GitHub Pages: $NWO is ${VIS:-of unknown visibility}.
Pages on a non-private repo serves your loop goals, outcomes, and signals to
the world. Setup files were still vendored; nothing was published.
  - Non-sensitive project and you accept public visibility? re-run with --public-ok
  - PHI-adjacent work? never enable this — see compliance/org-controls-audit.md
  - Private Pages needs GitHub Enterprise/Team (an org-level fact, not scriptable)
EOF
    exit 3
  fi
  if (cd "$REPO" && gh api -X POST "repos/$NWO/pages" -f build_type=github_actions >/dev/null 2>&1); then
    echo "Pages: enabled on $NWO (Source: GitHub Actions)"
  elif (cd "$REPO" && gh api -X PUT "repos/$NWO/pages" -f build_type=github_actions >/dev/null 2>&1); then
    echo "Pages: already enabled on $NWO — build_type set to github_actions"
  else
    echo "Pages: API call failed (admin rights needed on $NWO?); $MANUAL_PAGES"
  fi
fi

if [ "$PROTECT" = 1 ] && [ "$DRY" != 1 ]; then
  if [ "$GH_READY" = 1 ]; then
    DEF="$( (cd "$REPO" && gh repo view --json defaultBranchRef -q .defaultBranchRef.name) 2>/dev/null )"
    [ -n "$DEF" ] || DEF=main
    if (cd "$REPO" && gh api -X PUT "repos/$NWO/branches/$DEF/protection" --input - >/dev/null 2>&1 <<'JSON'
{"required_status_checks":null,"enforce_admins":false,"required_pull_request_reviews":{"required_approving_review_count":1},"restrictions":null}
JSON
    ); then
      echo "Protection: $DEF now requires 1 approving PR review"
    else
      echo "Protection: API call failed (admin rights needed?); set manually: Settings -> Branches"
    fi
  else
    echo "Protection: skipped — gh unavailable or repo unresolved (see Pages note above)"
  fi
fi

cat <<EOF
Next steps:
  1. Review what changed:  git -C $REPO status
  2. Land it team-style: commit on a feature branch, open a PR (never straight
     to the default branch — that is the point of team-ready).
  3. After the PR merges, trigger the first build and get the team URL:
       gh workflow run fleet-pages.yml
       gh api repos/${NWO:-<owner>/<repo>}/pages -q .html_url
EOF
