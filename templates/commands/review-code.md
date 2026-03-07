Perform a comprehensive review of all uncommitted changes.

## What this does
- Gathers and reviews all uncommitted changes in the current branch
- Produces a prioritized list of action items with file:line references
- Optionally posts findings to the relevant issue tracker

## Steps
1. Collect change context:
   - `git status --porcelain`
   - `git diff`
   - `git diff --cached`
   - `git diff HEAD`
   - `git log --oneline -n 5`
2. If an issue ID is provided or can be inferred from the branch name, read the issue to understand the intent.
3. Analyze changes for: security, performance, style, consistency, missing edge cases, dependency impacts, and integration risks.
4. Output a summary and a single prioritized action list using indicators:
   - RED — must-fix
   - YELLOW — recommended
   - GREEN — consider
5. If Linear MCP tools are available and an issue was identified, post the review as a comment on the issue.
6. If there are no action items, suggest the issue is ready for the next phase.

## Output template
```
## Code Review

Summary: <1-2 sentences>

Action Items:
1. <indicator> <action> in `path:line`
2. <indicator> <action> in `path:start-end`
```
