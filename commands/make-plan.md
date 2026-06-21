Break the chosen proposal into a concrete implementation plan.

## Behavior
- Do NOT write any code. Only create the plan.
- Clarify the code change scope, constraints, and ordering before creating anything.
- Use `${CLAUDE_PLUGIN_ROOT}/templates/design-doc-template.md` as a reference for what sections to cover.

## Steps
1. Read the relevant research and proposal documents.
2. If Linear MCP tools are available:
   - Create a **parent issue** that serves as the epic/tracker for the full plan. Include context, requirements, design decisions, and any security/testing notes in the description.
   - Break into ordered **sub-issues** under the parent, each small enough for a single commit. Include affected files, acceptance criteria, and blockers.
   - Set blocking relationships where steps depend on each other.
   - **Mark independence explicitly.** For each sub-issue, state whether it is *independent* (no blocking edge, touches a disjoint set of files) or *dependent*. This is what lets the Implement phase run independent slices in parallel (see `reppit.md` Phase 4). Two sub-issues that edit the same file are **not** independent — give them a blocking edge to force serialization.
3. If Linear is not available:
   - Create a `plans/` directory with a parent plan `.md` file and individual task `.md` files.
4. Regardless of whether Linear is available, also create Claude Code Tasks using `TaskCreate` for each sub-task. This provides persistent task tracking that survives across sessions.
   - **When invoked under a goal-loop** (`/reppit-goal`): tag each Task's `metadata` with the active `goalId` and a RICE score per `${CLAUDE_PLUGIN_ROOT}/commands/backlog-scoring.md`, so the sub-tasks join the prioritized backlog.
5. Present the plan to the user for review.

## Notes
- Keep solutions simple and focused. Only plan changes that are directly requested.
- Each sub-issue should map to a vertical slice when possible (DB + API + UI together).
