---
name: research-codebase
description: Document the existing codebase exactly as it is today (no suggestions, no fixes). Use as the first phase, before proposing changes.
---

<!-- GENERATED from commands/research-codebase.md by bin/build-codex-skills.py — do not edit here. -->

Research and document the existing codebase exactly as it is today; no suggestions or evaluations.

## Behavior contract
- Only document what exists today; do not suggest improvements, RCA, or future work.
- Provide concrete file paths and line references in findings.
- Read any user-mentioned files fully before decomposing work.

## Steps after receiving the research query
1. Read directly mentioned files fully.
2. Decompose the query into focused research areas and create an internal checklist.
3. Explore relevant directories and files in parallel when areas are independent. If necessary, inspect git history for additional context.
   - **Token discipline (see `.agents/skills/token-discipline/SKILL.md`):** for broad or deep exploration, delegate the heavy reading to `Explore`/`Agent` subagents — one per independent area — and bring back only their findings. The main thread should accumulate conclusions and code references, not raw file contents, so later phases inherit a lean context window.
4. Synthesize after all exploration completes; prioritize live code findings over historical docs.
5. Produce a structured research document.
   - If Linear MCP tools are available, save it as a Linear document.
   - Also save a copy to the local `research/` directory for reference during later phases.

## Output format
- High-level summary (3-6 sentences)
- Detailed findings grouped by component/area
- Code references in the form `path/to/file.py:123-145`
