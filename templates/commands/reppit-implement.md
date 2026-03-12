Continue the RePPITS workflow. The plan has been approved — now execute Implement → Test → Secure.

## Phase 4 — Implement (per sub-task)

<!-- PHASE:implement -->

## Task Tracking

Before starting implementation:
1. Call `TaskList` to see all current tasks and their statuses.
2. Identify the next `open` task to work on.
3. If all tasks are already `completed`, skip to Phase 5 (Test).

For each sub-task in the approved plan, in order:

1. Call `TaskUpdate` to set the task status to `in_progress`.
2. Follow `.claude/commands/implement.md` if available.
3. After implementing each sub-task, commit the changes.
4. Call `TaskUpdate` to set the task status to `completed`.
5. Move to the next open task.

When all sub-tasks are implemented, proceed to Phase 5.

## Phase 5 — Test

<!-- PHASE:test -->

Follow `.claude/commands/review-code.md` to review all changes if available.

- If review has action items → fix them and re-review.
- Loop (implement fix → re-test) until the review is clean.
- When clean, proceed to Phase 6.

## Phase 6 — Secure

<!-- PHASE:secure -->

Follow `.claude/commands/secure.md` to run security checks against all changes if available.

For each enabled framework (HIPAA, SOC2, HITRUST), emit structured compliance results:

<!-- SECURE:hipaa:START -->
For each HIPAA checklist item, emit:
<!-- SECURE_ITEM:pass|warn|fail:Check Name:Detail about the finding -->
<!-- SECURE:hipaa:END -->

<!-- SECURE:soc2:START -->
For each SOC2 checklist item, emit:
<!-- SECURE_ITEM:pass|warn|fail:Check Name:Detail about the finding -->
<!-- SECURE:soc2:END -->

<!-- SECURE:hitrust:START -->
For each HITRUST checklist item, emit:
<!-- SECURE_ITEM:pass|warn|fail:Check Name:Detail about the finding -->
<!-- SECURE:hitrust:END -->

- If there are FAIL items:
  1. Fix the security issues
  2. Re-run Test (Phase 5) to verify fixes don't break anything
  3. Re-run Secure to check again
  4. Repeat until no FAIL items remain
- WARN items: note them in the summary.
- When all checks pass, commit all changes.

## Rules
- Implement all sub-tasks from the approved plan.
- All phases proceed automatically — do not wait for user input.
- Keep all context from the planning conversation.
