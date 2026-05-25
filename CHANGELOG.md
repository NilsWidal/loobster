# Changelog

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
