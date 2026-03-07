Research and document the existing codebase exactly as it is today; no suggestions or evaluations.

## Behavior contract
- Only document what exists today; do not suggest improvements, RCA, or future work.
- Provide concrete file paths and line references in findings.
- Read any user-mentioned files fully before decomposing work.

## Steps after receiving the research query
1. Read directly mentioned files fully.
2. Decompose the query into focused research areas and create an internal checklist.
3. Explore relevant directories and files in parallel when areas are independent. If necessary, inspect git history for additional context.
4. Synthesize after all exploration completes; prioritize live code findings over historical docs.
5. Produce a structured research document.
   - If Linear MCP tools are available, save it as a Linear document.
   - Also save a copy to the local `research/` directory for reference during later phases.

## Output format
- High-level summary (3-6 sentences)
- Detailed findings grouped by component/area
- Code references in the form `path/to/file.py:123-145`
