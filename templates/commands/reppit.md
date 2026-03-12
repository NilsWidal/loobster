Run the RePPITS workflow. This message covers Research → Propose → Plan.

Input: A topic, feature description, or issue identifier.

## Phase 1 — Research

<!-- PHASE:research -->

Research the existing codebase thoroughly. Follow the instructions in `.claude/commands/research-codebase.md` if available.

Present a brief findings summary, then immediately proceed to Phase 2.

## Phase 2 — Propose

<!-- PHASE:propose -->

Based on the research, propose up to 2 solution approaches. Follow `.claude/commands/make-proposals.md` if available.

Present both proposals briefly, pick the stronger one (or the one that better fits codebase conventions), then proceed to Phase 3.

## Phase 3 — Plan

<!-- PHASE:plan -->

Create a detailed implementation plan based on the chosen proposal. Follow `.claude/commands/make-plan.md` if available.

Break the work into concrete sub-tasks. Present the full plan clearly.

**IMPORTANT: After presenting the plan, STOP. Do not proceed to implementation.** The user will review the plan and respond in the next message. Do not ask "shall I proceed" — just present the plan and end your response.

## Task Persistence

At the very start, call `TaskList` to check for existing tasks from a prior session. If tasks already exist, present their status and continue from where you left off instead of starting fresh.

After presenting the plan, create a persistent task for each sub-task using `TaskCreate`:
- Title: a short description of the sub-task
- Description: acceptance criteria and affected files
- Status: `open`

This ensures tasks survive across sessions and context compaction.

## Rules
- At the start of each phase, output the phase marker (e.g. `<!-- PHASE:research -->`) on its own line exactly as shown above.
- Complete all three phases (Research → Propose → Plan) in this single response.
- Do NOT start implementing. Stop after presenting the plan.
- Keep context between phases — don't re-read files you already have in context.
