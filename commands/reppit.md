Run the full RePPITS workflow: Research → Propose → Plan → Implement → Test → Secure.

Input: Either a topic/feature description OR a Linear issue identifier (e.g., `CAR-123`).
If a Linear issue is provided, read it first to extract the task description.

## Arguments
- **topic**: The feature description or Linear issue ID — required
- **ralph**: If the user says "with ralph", activate Ralph Loop during the Implement phase
- **--auto**: Allow trivial-tier tasks to auto-advance the early phases (see Phase 0). Off by default — without this flag every phase still stops at its gate.
- **--manual**: Force every gate for every tier, overriding all auto-advance. Use for maximum oversight regardless of risk classification.

## Phase 0 — Right-size

Before any research, classify the task so the workflow can adapt its gates to the risk. Restate the task in one line, then assign a **tier**:

- **trivial** — a localized, low-risk change (typo, copy, comment, doc tweak, a single obvious one-liner) that touches no PHI, auth, crypto, access control, data retention, or infrastructure.
- **standard** — a normal feature or fix: multiple files or a vertical slice, but no direct handling of PHI/auth/infra.
- **sensitive** — touches (or plausibly touches) PHI, authentication/authorization, encryption, audit logging, data retention/deletion, multi-tenant isolation, or infrastructure (CDK/K8s/CI-CD). **When in doubt between standard and sensitive, choose sensitive.**

State the chosen tier and a one-sentence justification, then apply the gate policy below.

### Gate policy by tier

| Tier | Research / Propose / Plan gates | Implement gate (per sub-issue) | Test gate | Secure phase | Secure gate |
|------|-------------------------------|-------------------------------|-----------|--------------|-------------|
| **trivial** | Auto-advance **only if `--auto`** (else gated); collapse to a single review before commit | Gated | Gated | Run (still required) | Gated |
| **standard** | Gated (today's behavior) | Gated | Gated | Run | Gated |
| **sensitive** | Gated — **never** auto-advance, even with `--auto` | Gated | Gated | **Mandatory, never skippable** | Gated — blocks on any FAIL |

Rules that override the table:
- `--manual` forces every gate for every tier (ignores `--auto`).
- The **Secure phase always runs** for every tier — `--auto` may collapse *review gates*, never the security check itself.
- For **sensitive**, `--auto` is ignored entirely.

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

Present the created plan structure (parent + sub-issues) to the user — as Linear issues if Linear MCP is available, otherwise as local `plans/*.md` files.

**Gate 3 — Plan Review:**
- Ask: "Plan created. OK to start implementing, or do you want changes?"
- If the user gives feedback → update the plan (Linear issues if available, else the local `plans/` files and Claude Code Tasks) and present again. Loop until OK.
- If OK → proceed to Phase 4.

## Phase 4 — Implement (per sub-issue)

Order the sub-issues by their dependency edges (from Phase 3). Then, **when subagents are available** (`Agent` tool) and the tier is standard/sensitive (a trivial-tier task is small enough to implement serially):

- **Implement independent sub-issues in parallel.** Sub-issues with no open `blockedBy` edge and a disjoint file set can be implemented concurrently, each in its own `Agent` with `isolation: "worktree"` so parallel edits don't collide. Wall-clock becomes the slowest slice, not the sum.
- **Serialize dependent sub-issues.** A sub-issue runs only after the tasks it is `blockedBy` are complete. Two sub-issues touching the same file are treated as dependent.
- **If subagents are not available** (e.g. a minimal Agent SDK harness or a client without the `Agent` tool), fall back to implementing sub-issues serially in order — the workflow degrades gracefully (Tier 0).

For each sub-issue:

1. Follow `${CLAUDE_PLUGIN_ROOT}/commands/implement.md` for the sub-issue.
   - If Ralph Loop was requested ("with ralph"): check whether the `/ralph-loop:ralph-loop` command exists. If it does, invoke it for implementation. If it does **not** (the external plugin isn't installed), say so and fall back to the built-in bounded convergence loop described in Phase 6 — do not error on the missing command.

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
- If there are FAIL items, run the **bounded autonomous convergence loop** (no gate between iterations — this is the one place the workflow self-drives):
  1. Implement the security fixes (back to Implement phase logic)
  2. Re-run Test (Phase 5) to verify fixes don't break anything
  3. Re-run Secure to check again
  4. Repeat this Implement → Test → Secure loop until no FAIL items remain **or** the iteration cap is reached.
  - **Iteration cap: 3.** If FAILs remain after 3 full iterations, **escalate**: stop the loop, summarize the remaining FAILs, the fixes attempted each iteration, and why they didn't converge — then hand control back to the user. **Never** silently commit or push past unresolved FAILs.
  - On long-running loops, externalize progress after each iteration (write the iteration outcome to the plan/Tasks) so a resumed session can continue, and self-pace rather than blocking on a human tick.
- WARN items: present to user for acknowledgment.
- When clean (or warnings acknowledged), ask: "Security check passed. Ready to commit and push?"
- If OK → commit all changes; mark the work done in your tracker — update Linear issues to Done if Linear is available, and mark the corresponding Claude Code Tasks `completed`.
- Play notification sound, then ask: "What branch name?" and offer to create a PR.

## Rules
- **Gates follow the Phase 0 tier policy.** By default every gate is active (wait for explicit user approval before advancing). Only the trivial tier with `--auto` may collapse the early review gates, and `--manual` forces all gates. The **Secure phase and Gate 6 are never skipped for any tier**, and **sensitive tier never auto-advances**.
- The Phase 6 convergence loop is the sole exception that self-drives between iterations, and it is bounded (cap 3) and escalates to the user — it never bypasses Gate 6's final approval.
- **At every active gate**, before asking the user a question, run `afplay /System/Library/Sounds/Glass.aiff &` to play a notification sound so the user knows input is needed.
- Apply the token-discipline conventions in `${CLAUDE_PLUGIN_ROOT}/commands/token-discipline.md` throughout: delegate heavy reads to subagents and forward only conclusions, pass artifact summaries between phases (re-reading files on demand), and keep stable context stable.
- Keep all context between phases — don't re-read files you already have in context.
- If the user says "stop" or "pause" at any point, halt and summarize current state.
- If the user wants to skip a phase (e.g., "skip research, go straight to plan"), that's allowed — just confirm and jump ahead.
