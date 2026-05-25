Implement the work described in an issue or task.

## Arguments
- **issue**: Issue ID (e.g., Linear identifier like `CAR-123`) or path to a local plan `.md` file — required

## Steps
1. Read the issue or task file.
   - If a Linear ID is provided and Linear MCP tools are available, read the Linear issue.
   - If the issue has a parent, read it for broader context and design decisions.
   - If a local `.md` path is provided, read that file.
2. If Linear is available, set the issue status to **"In Progress"**.
3. Implement the changes described in the issue, following the acceptance criteria.
4. After implementation, present a summary of what was changed and which files were touched.

## Notes
- Follow all project conventions from CLAUDE.md or similar project documentation.
- Only make changes described in the issue. Keep solutions simple and focused.
- If the issue description is ambiguous or missing information, ask the user before writing code.
