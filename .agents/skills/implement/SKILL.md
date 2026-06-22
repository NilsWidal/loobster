---
name: implement
description: Implement a single planned issue, optionally inside a bounded autonomous loop. Use to execute one unit of an approved plan.
---

<!-- GENERATED from commands/implement.md by bin/build-codex-skills.py — do not edit here. -->

Implement the work described in an issue or task.

## Arguments
- **issue**: Issue ID (e.g., Linear identifier like `CAR-123`) or path to a local plan `.md` file — required

## Steps
1. Read the issue or task file.
   - If a Linear ID is provided and Linear MCP tools are available, read the Linear issue.
   - If the issue has a parent, read it for broader context and design decisions.
   - If a local `.md` path is provided, read that file.
   - If a matching Claude Code Task exists (find it via `TaskList`), read it with `TaskGet` for the latest state and dependencies.
2. Mark work as started:
   - If Linear is available, set the issue status to **"In Progress"**.
   - If a Claude Code Task tracks this work, `TaskUpdate` it to `in_progress`. This is what makes the work resumable across sessions (see `/resume`).
3. Implement the changes described in the issue, following the acceptance criteria.
4. Mark work complete:
   - `TaskUpdate` the Claude Code Task to `completed` **only** when the work is fully done (no failing checks, no partial implementation). If blocked, keep it `in_progress` and note the blocker.
   - If Linear is available, advance the issue status per your team's flow.
5. After implementation, present a summary of what was changed and which files were touched.

## Notes
- Follow all project conventions from CLAUDE.md or similar project documentation.
- Only make changes described in the issue. Keep solutions simple and focused.
- If the issue description is ambiguous or missing information, ask the user before writing code.
