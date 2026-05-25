Run the full RePPITS workflow: Research → Propose → Plan → Implement → Test → Secure.

Input: Either a topic/feature description OR a Linear issue identifier (e.g., `CAR-123`).
If a Linear issue is provided, read it first to extract the task description.

## Arguments
- **topic**: The feature description or Linear issue ID — required
- **ralph**: If the user says "with ralph", activate Ralph Loop during the Implement phase

## Phase 1 — Research

Follow the instructions in `${CLAUDE_PLUGIN_ROOT}/commands/research-codebase.md`.

After completing research, present the findings summary to the user.

**Gate 1 — Research Review:**
- Ask: "Research complete. OK to proceed to proposals, or do you have feedback?"
- If the user gives feedback → refine the research and present again. Loop until OK.
- If OK → proceed to Phase 2.

## Phase 2 — Propose

Follow the instructions in `${CLAUDE_PLUGIN_ROOT}/commands/make-proposals.md`, using the research from Phase 1.

Present both proposals to the user.

**Gate 2 — Proposal Review:**
- Ask: "Which proposal do you prefer (1 or 2), or do you have feedback to refine?"
- If the user gives feedback → refine proposals and present again. Loop until a choice is made.
- If the user picks one → proceed to Phase 3 with the chosen proposal.

## Phase 3 — Plan

Follow the instructions in `${CLAUDE_PLUGIN_ROOT}/commands/make-plan.md`, using the chosen proposal from Phase 2.

Present the created Linear issue structure (parent + sub-issues) to the user.

**Gate 3 — Plan Review:**
- Ask: "Plan created in Linear. OK to start implementing, or do you want changes?"
- If the user gives feedback → update the Linear issues accordingly and present again. Loop until OK.
- If OK → proceed to Phase 4.

## Phase 4 — Implement (per sub-issue)

For each sub-issue created in Phase 3, in order:

1. Follow `${CLAUDE_PLUGIN_ROOT}/commands/implement.md` for the sub-issue.
   - If Ralph Loop was requested, invoke `/ralph-loop:ralph-loop` for implementation.

**Gate 4 — Implementation Review (per sub-issue):**
- Ask: "Sub-issue implemented. Commit and move to next?"
- If the user gives feedback → refine and present again. Loop until OK.
- If OK → commit, move to next sub-issue.

## Phase 5 — Test

After all sub-issues are implemented, follow `${CLAUDE_PLUGIN_ROOT}/commands/review-code.md` to review all changes.

**Gate 5 — Test Review:**
- If review has action items → fix them and re-review. Loop until clean.
- When clean, ask: "All tests and review passed. Proceed to security check?"
- If OK → proceed to Phase 6.

## Phase 6 — Secure

Follow `${CLAUDE_PLUGIN_ROOT}/commands/secure.md` to run HIPAA/SOC2/HITRUST security checks against all changes.

**Gate 6 — Security Review:**
- If there are FAIL items:
  1. Implement the security fixes (back to Implement phase logic)
  2. Re-run Test (Phase 5) to verify fixes don't break anything
  3. Re-run Secure to check again
  4. Repeat this Implement → Test → Secure loop until no FAIL items remain
- WARN items: present to user for acknowledgment.
- When clean (or warnings acknowledged), ask: "Security check passed. Ready to commit and push?"
- If OK → commit all changes, update Linear issues to Done.
- Play notification sound, then ask: "What branch name?" and offer to create a PR.

## Rules
- NEVER skip a gate. Always wait for explicit user approval before advancing.
- **At every gate**, before asking the user a question, run `afplay /System/Library/Sounds/Glass.aiff &` to play a notification sound so the user knows input is needed.
- Keep all context between phases — don't re-read files you already have in context.
- If the user says "stop" or "pause" at any point, halt and summarize current state.
- If the user wants to skip a phase (e.g., "skip research, go straight to plan"), that's allowed — just confirm and jump ahead.
