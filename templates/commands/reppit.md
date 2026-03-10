Run the full RePPITS workflow: Research, Propose, Plan, Implement, Test, Secure.

Input: A topic, feature description, or issue identifier.

## Arguments
- **topic**: The feature description or issue ID — required

## Phase 1 — Research

<!-- PHASE:research -->

Follow the instructions in `.claude/commands/research-codebase.md`.

After completing research, present a brief findings summary and immediately proceed to Phase 2.

## Phase 2 — Propose

<!-- PHASE:propose -->

Follow the instructions in `.claude/commands/make-proposals.md`, using the research from Phase 1.

Present both proposals briefly, pick the stronger one (or the one that better fits the codebase conventions), and proceed to Phase 3.

## Phase 3 — Plan

<!-- PHASE:plan -->

Follow the instructions in `.claude/commands/make-plan.md`, using the chosen proposal from Phase 2.

Present the full plan (issues or local `.md` files) to the user.

**Gate — Plan Review:**
<!-- GATE:plan:prompt:Plan ready for review. OK to start implementing, or do you want changes? -->
- If the user gives feedback → update the plan and present again. Loop until OK.
- If OK → proceed to Phase 4.

## Phase 4 — Implement (per sub-issue)

<!-- PHASE:implement -->

For each sub-issue or task created in Phase 3, in order:

1. Follow `.claude/commands/implement.md` for the sub-issue.
2. After implementing each sub-issue, commit and move to the next.

When all sub-issues are implemented, proceed to Phase 5.

## Phase 5 — Test

<!-- PHASE:test -->

Follow `.claude/commands/review-code.md` to review all changes.

- If review has action items → fix them and re-review.
- Loop (implement fix → re-test) until the review is clean.
- When clean, proceed to Phase 6.

## Phase 6 — Secure

<!-- PHASE:secure -->

Follow `.claude/commands/secure.md` to run security checks against all changes.

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
  1. Fix the security issues (back to Implement)
  2. Re-run Test (Phase 5) to verify fixes don't break anything
  3. Re-run Secure to check again
  4. Repeat Implement → Test → Secure until no FAIL items remain
- WARN items: note them in the summary.
- When all checks pass, commit all changes.

<!-- DONE -->

## Rules
- Present the plan at the Plan phase gate and wait for explicit user approval before implementing.
- All other phases proceed automatically — do not wait for user input.
- Keep all context between phases — don't re-read files you already have in context.
- If the user says "stop" or "pause" at any point, halt and summarize current state.
