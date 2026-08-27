---
name: team-setup
description: Wire a repo for Loobster's team layer in one command: vendor the fleet dashboard workflow + the scripts it runs in CI, scaffold signals/ and plans/loop/, and enable GitHub Pages via gh (refusing on public repos unless explicitly overridden). Use when onboarding a repo to the team features.
---

<!-- GENERATED from commands/team-setup.md by bin/build-codex-skills.py — do not edit here. -->

Make this repo **team-ready on GitHub in one command**: vendor the fleet dashboard workflow (plus the scripts it runs in CI), scaffold the signals hub and the loop-marker directory, and enable GitHub Pages — so the team gets one URL showing every loop on every branch, with Pause / Resume / Stop that commit back. GitHub is the server: Actions is the runtime, Pages is the UI, git is the only data plane.

## Why files are copied, not referenced

`fleet-pages.yml` runs `python3 bin/fleet-build.py` and `bin/signals-build.py` from the **repo checkout inside Actions**, where the plugin install directory does not exist. A hand-copied workflow without the scripts fails on its first run. So setup vendors the workflow *and* its scripts into the repo, each stamped `vendored from loobster vX.Y.Z`. After a plugin upgrade, re-run with `--force` to refresh the copies.

## Steps

1. **Preflight.** Confirm the workspace is a git repo. Check `gh auth status`; if `gh` is missing or unauthenticated, still proceed — the script vendors everything and prints the one manual step (Settings → Pages → Source: GitHub Actions) instead of doing it via API.
2. **Compliance gate — before running.** The real question is not "is the repo private?" but "will the *Pages site* be world-readable?" — and it will be for every repo **except a private repo on GitHub Enterprise Cloud** (a private repo on Free/Pro/Team still publishes public Pages). The script checks visibility **and** plan and refuses (exit 3) whenever the board would be public, unless `--public-ok`. So: if it refuses, stop and ask the human explicitly before passing `--public-ok` — the board would expose loop goals, task titles, and signals. **Never** on PHI-adjacent work — see `compliance/org-controls-audit.md`. After enabling, the script reads the live Pages object back and prints whether the URL is actually public or private; relay that to the human.
3. **Run it:**
   ```bash
   bash bin/team-init.sh --repo "$(pwd)"
   ```
   Flags to pass through when asked: `--protect-main` (require 1 approving PR review on the default branch — pairs with `pr-lane` loops, where PR review *is* the human gate), `--no-pages` (wire files only), `--dry-run` (show the plan first), `--force` (refresh vendored copies after an upgrade).
4. **Heed the script's warnings.** If it reports an existing `signals-pages.yml`, remove that workflow in the same change — one Pages site per repo; the fleet board serves signals at `/signals/`.
5. **Land it team-style.** Review `git status` / `git diff`, commit on a feature branch, open a PR. Never commit straight to the default branch — that is the point of team-ready.
6. **After the PR merges**, trigger the first build and hand the team URL back:
   ```bash
   gh workflow run fleet-pages.yml
   gh api repos/<owner>/<repo>/pages -q .html_url
   ```
   (`workflow_dispatch` only works once the workflow file is on the default branch — do not try it before the merge.)

## Notes

- Re-runs are safe: existing files are skipped without `--force`, so `/team-setup` is also the upgrade path for the vendored scripts.
- Genuinely private Pages requires **GitHub Enterprise Cloud** — an org-level fact the script cannot change. On any other plan a "private" repo still serves a fully public Pages site (not merely unlisted), which is why the gate blocks it by default; see `compliance/org-controls-audit.md`.
- This wires the *team layer* only. The RePPITS workflow itself (`/run`, `/loop`, `/secure`) needs no setup.
