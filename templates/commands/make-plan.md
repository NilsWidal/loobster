Break the chosen proposal into a concrete implementation plan.

## Behavior
- Do NOT write any code. Only create the plan.
- Clarify the code change scope, constraints, and ordering before creating anything.
- Use `.claude/design_doc_template.md` as a reference for what sections to cover (if it exists).

## Steps
1. Read the relevant research and proposal documents.
2. If Linear MCP tools are available:
   - Create a **parent issue** that serves as the epic/tracker for the full plan. Include context, requirements, design decisions, and any security/testing notes in the description.
   - Break into ordered **sub-issues** under the parent, each small enough for a single commit. Include affected files, acceptance criteria, and blockers.
   - Set blocking relationships where steps depend on each other.
3. If Linear is not available:
   - Create a `plans/` directory with a parent plan `.md` file and individual task `.md` files.
4. Regardless of whether Linear is available, also create Claude Code Tasks using `TaskCreate` for each sub-task. This provides persistent task tracking that survives across sessions.
5. Present the plan to the user for review.

## Notes
- Keep solutions simple and focused. Only plan changes that are directly requested.
- Each sub-issue should map to a vertical slice when possible (DB + API + UI together).
