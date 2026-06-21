# Contributing to Loobster

Thanks for your interest in contributing.

## Repository layout

```
.claude-plugin/
  plugin.json           — plugin manifest (name, version, metadata)
  marketplace.json      — marketplace entry consumed by `/plugin marketplace add`
commands/
  reppit.md             — orchestrator slash command for the full workflow
  reppit-loop.md        — /reppit-loop (goal-loop)
  signals.md            — /signals (shared team hub)
  verify-frontend.md    — /verify-frontend (Playwright verification)
  backlog-scoring.md    — RICE scoring convention (shared)
  token-discipline.md   — token conventions (shared)
  resume-reppit.md      — /resume-reppit
  research-codebase.md  — /research-codebase
  make-proposals.md     — /make-proposals
  make-plan.md          — /make-plan
  implement.md          — /implement
  review-code.md        — /review-code
  secure.md             — /secure
bin/
  signals-build.py · screenshot.mjs · loobster.sh · headroom-compress.py
templates/
  signals-dashboard.html · signals-pages.yml · playwright-verify.yml · design-doc-template.md
compliance/
  frameworks.md         — enable/disable config + profiles
  hipaa-checklist.md · hitrust-checklist.md · iso27001-checklist.md · soc2-checklist.md
  org-controls-audit.md
```

The slash commands cross-reference each other using `${CLAUDE_PLUGIN_ROOT}`, which Claude Code resolves to the plugin's install directory at runtime.

## Develop locally

1. Fork and clone the repo.
2. In a test workspace, add the local clone as a marketplace and install:
   ```
   /plugin marketplace add /absolute/path/to/your/loobster
   /plugin install loobster@nilswidal-loobster
   ```
3. Edit any `commands/*.md` or `compliance/*.md` file. Re-run `/plugin marketplace update` then `/plugin install` to pick up changes.
4. Test the slash commands against a real workspace.

## Submitting changes

1. Branch from `main`.
2. Make focused changes, one concern per PR.
3. Bump the version in `.claude-plugin/plugin.json` and add a `CHANGELOG.md` entry.
4. Open a PR describing what changed and why.

## Customizing checklists

The compliance checklists are intentionally generic and tuned for SaaS healthcare. If you have domain-specific checks (FDA, GDPR, state-level regs), consider contributing them as additional optional checklist files rather than editing the existing ones.

## License

By contributing, you agree your contributions will be licensed under Apache 2.0.
