Run the full RePPITS workflow: Research, Propose, Plan, Implement, Test, Secure.

Input: A topic, feature description, or issue identifier.

## Arguments
- **topic**: The feature description or issue ID — required

## Phase 1 — Research

<!-- PHASE:research -->

Follow the instructions in `.claude/commands/research-codebase.md`.

After completing research, present the findings summary to the user.

**Gate 1 — Research Review:**
<!-- GATE:research:prompt:Research complete. OK to proceed to proposals, or do you have feedback? -->
- If the user gives feedback → refine the research and present again. Loop until OK.
- If OK → proceed to Phase 2.

## Phase 2 — Propose

<!-- PHASE:propose -->

Follow the instructions in `.claude/commands/make-proposals.md`, using the research from Phase 1.

Present both proposals to the user.

**Gate 2 — Proposal Review:**
<!-- GATE:propose:options:1,2:prompt:Which proposal do you prefer (1 or 2), or do you have feedback to refine? -->
- If the user gives feedback → refine proposals and present again. Loop until a choice is made.
- If the user picks one → proceed to Phase 3 with the chosen proposal.

## Phase 3 — Plan

<!-- PHASE:plan -->

Follow the instructions in `.claude/commands/make-plan.md`, using the chosen proposal from Phase 2.

Present the plan (issues or local `.md` files) to the user.

**Gate 3 — Plan Review:**
<!-- GATE:plan:prompt:Plan created. OK to start implementing, or do you want changes? -->
- If the user gives feedback → update the plan and present again. Loop until OK.
- If OK → proceed to Phase 4.

## Phase 4 — Implement (per sub-issue)

<!-- PHASE:implement -->

For each sub-issue or task created in Phase 3, in order:

1. Follow `.claude/commands/implement.md` for the sub-issue.

**Gate 4 — Implementation Review (per sub-issue):**
<!-- GATE:implement:prompt:Sub-issue implemented. Commit and move to next? -->
- If the user gives feedback → refine and present again. Loop until OK.
- If OK → commit, move to next sub-issue.

## Phase 5 — Test

<!-- PHASE:test -->

After all sub-issues are implemented, follow `.claude/commands/review-code.md` to review all changes.

**Gate 5 — Test Review:**
- If review has action items → fix them and re-review. Loop until clean.
<!-- GATE:test:prompt:All tests and review passed. Proceed to security check? -->
- If OK → proceed to Phase 6.

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

**Gate 6 — Security Review:**
- If there are FAIL items:
  1. Fix the security issues (back to Implement)
  2. Re-run Test (Phase 5) to verify fixes don't break anything
  3. Re-run Secure to check again
  4. Repeat Implement → Test → Secure until no FAIL items remain
- WARN items: present to user for acknowledgment.
<!-- GATE:secure:prompt:Security check passed. Ready to commit and push? -->
- If OK → commit all changes.

<!-- DONE -->

## Rules
- NEVER skip a gate. Always wait for explicit user approval before advancing.
- Keep all context between phases — don't re-read files you already have in context.
- If the user says "stop" or "pause" at any point, halt and summarize current state.
- If the user wants to skip a phase, confirm and jump ahead.
