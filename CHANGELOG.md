# Changelog

## 0.3.0 — Autonomous loops & dynamic workflows

- **Adaptive gating (Phase 0):** `/reppit` now right-sizes each task (trivial / standard / sensitive) and applies a gate policy per tier. New `--auto` (let trivial tasks auto-advance early phases) and `--manual` (force all gates) flags. Sensitive tasks never auto-advance; the Secure phase always runs for every tier.
- **Bounded autonomous convergence loop:** the Implement→Test→Secure fix loop self-drives up to 3 iterations, then escalates to a human — never silently commits past unresolved FAILs.
- **Resumable workflows:** real Claude Code Tasks status lifecycle across Implement/Test/Secure, plus a new `/resume-reppit` command that rebuilds state from `TaskList` after a crash or new session.
- **Tier-1 parallelism:** independent sub-issues (disjoint files, no blocking edge) are implemented concurrently in isolated worktrees via subagents; degrades to serial when subagents aren't available.
- **Ralph fallback:** the optional `with ralph` path now detects whether `/ralph-loop:ralph-loop` is installed and falls back to the built-in bounded loop instead of erroring.
- **Native token discipline (Option A):** new `commands/token-discipline.md` — subagent isolation, artifact compaction, cache-stable prefixes, terse output. Always on, zero-dependency, portable.
- **Optional headroom compression (Option D):** opt-in, default-OFF `PostToolUse` hook (`hooks/hooks.json` + `bin/headroom-compress.py`) that compresses large tool outputs via a locally-installed [headroom](https://github.com/chopratejas/headroom) when `REPPIT_HEADROOM=1`. Graceful passthrough otherwise. Tests in `tests/test-headroom-hook.sh`. Healthcare PHI-data-path caveat documented in the README and `compliance/org-controls-audit.md`.
- Tier-2 deterministic Workflow harness (subagents + Workflow-tool orchestration) is designed and tracked as a follow-up epic in `plans/autonomous-loops/`.

## 0.2.0 — Plugin pivot

- Repackaged as a Claude Code plugin (was a VS Code / Cursor extension)
- Installable via `/plugin marketplace add carainc/reppit-health`
- Seven slash commands: `/reppit`, `/research-codebase`, `/make-proposals`, `/make-plan`, `/implement`, `/review-code`, `/secure`
- Cross-references inside commands use `${CLAUDE_PLUGIN_ROOT}` for plugin-local paths, with `.claude/compliance/*.md` workspace overrides supported by `/secure`
- Extension scaffold (`src/`, `dist/`, `package.json`, VSIX, sidebar webview) removed; full history preserved at the `pre-plugin-pivot` git tag

## 0.1.0 — Initial Release (VS Code / Cursor extension, archived)

- Full RePPITS workflow: Research, Propose, Plan, Implement, Test, Secure
- Visual sidebar with phase stepper, gate prompts, and real-time log
- HIPAA, SOC2, and HITRUST compliance checklists with pass/warn/fail reporting
- Sound and system notifications at workflow gates
- Optional Linear integration (auto-detected via MCP, falls back to local .md files)
- Scaffoldable command templates (`RePPIT: Initialize Project Templates`)
- Standalone `/secure` command for ad-hoc security checks
- Works in VS Code and Cursor
