Run the full RePPITS workflow: Research → Propose → Plan → Implement → Test → Secure.

Input: Either a topic/feature description OR a Linear issue identifier (e.g., `CAR-123`).
If a Linear issue is provided, read it first to extract the task description.

## Arguments
- **topic**: The feature description or Linear issue ID — required
- **--autonomous**: Pre-select autonomous execution — equivalent to choosing "Run autonomously" at Gate 3 (see Phase 4). After the plan is approved, drive the full **Implement → Test → Secure** loop without stopping at the per-sub-issue (Gate 4) or test (Gate 5) review prompts, halting only on escalation (loop cap) or at the **final commit/push approval**. Bounded (cap 3) and escalates on failure. Off by default. Even for the sensitive tier, Test and Secure still **run and block on findings**, and the final commit/push approval always stops — autonomous mode skips the intermediate *"shall I proceed?"* prompts, never the security checks themselves.
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
- `--manual` forces every gate for every tier (ignores `--auto` and autonomous mode).
- The **Secure phase always runs** for every tier — neither `--auto` nor autonomous mode ever skips the security check itself.
- For **sensitive**, `--auto` is ignored entirely (early phases stay gated).
- This table governs the `--auto` early-phase policy. **Autonomous mode** (chosen separately at Gate 3) is orthogonal: it auto-advances the *Implement (Gate 4)* and *Test (Gate 5)* review prompts for any tier so the Implement→Test→Secure loop runs continuously — but Test and Secure still **run and block on findings**, and the **final commit/push approval always stops**.

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

**Gate 3 — Plan Review (this is the kickoff point):**
- Ask: "Plan ready. **(a) Run autonomously**, **(b) step through each sub-issue**, or **(c) make changes**?"
  - **(c) Changes** → update the plan (Linear issues if available, else the local `plans/` files and Claude Code Tasks) and present again. Loop until the user picks (a) or (b).
  - **(b) Step through** (default) → proceed to Phase 4 in **review mode**: stop at Gate 4 after each sub-issue.
  - **(a) Run autonomously** → proceed to Phase 4 in **autonomous mode** (defined in Phase 4). `--autonomous` at invocation pre-selects this. For every tier, Test and Secure still **run and block on findings**, and the **final commit/push approval always stops** — autonomous mode skips the intermediate review prompts, not the security checks.
- Autonomous mode is what "kicks off" execution after planning: once chosen, the workflow drives the whole **Implement → Test → Secure** loop itself (Phases 4–6, no stops at Gates 4 or 5), pausing only to escalate a stuck loop or at the final commit/push approval.

## Phase 4 — Implement (per sub-issue)

Order the sub-issues by their dependency edges (from Phase 3). Then, **when subagents are available** (`Agent` tool) and the tier is standard/sensitive (a trivial-tier task is small enough to implement serially):

- **Implement independent sub-issues in parallel.** Sub-issues with no open `blockedBy` edge and a disjoint file set can be implemented concurrently, each in its own `Agent` with `isolation: "worktree"` so parallel edits don't collide. Wall-clock becomes the slowest slice, not the sum.
  - **Permission caveat (important):** worktree-isolated subagents write into a fresh `.claude/worktrees/<id>/` path, and subagents do **not** inherit a session's runtime `--dangerously-skip-permissions` flag — they resolve their mode from settings. If `permissions.defaultMode` is `auto` (or `default`), the auto-mode classifier evaluates each subagent's tool calls and you will get write-permission prompts mid-run, **even if the main session shows bypass**. To run parallel/worktree sub-issues prompt-free, set `permissions.defaultMode: "bypassPermissions"` in settings (pair it with a `deny` list for guardrails) — or skip worktree isolation and implement serially. Don't rely on the launch flag alone.
- **Serialize dependent sub-issues.** A sub-issue runs only after the tasks it is `blockedBy` are complete. Two sub-issues touching the same file are treated as dependent.
- **If subagents are not available** (e.g. a minimal Agent SDK harness or a client without the `Agent` tool), fall back to implementing sub-issues serially in order — the workflow degrades gracefully (Tier 0).

For each sub-issue:

1. Follow `${CLAUDE_PLUGIN_ROOT}/commands/implement.md` for the sub-issue, running it in the **built-in bounded loop** — iterate implement→test until the sub-issue's acceptance criteria and tests pass, **or** the cap (3) is reached, then **escalate** (stop and summarize what's blocking). This is the same bounded-loop mechanism the Secure phase uses (Phase 6); no external plugin is required.
2. Then continue according to the mode chosen at Gate 3:
   - **Review mode (step through):** stop at **Gate 4** for this sub-issue before continuing.
   - **Autonomous mode:** do **not** stop — commit the sub-issue, `TaskUpdate` it to `completed`, and continue straight to the next available sub-issue. Once all sub-issues are done, **continue automatically into Phase 5 (Test) and Phase 6 (Secure) without stopping at Gate 4 or Gate 5** — autonomous mode drives the whole Implement → Test → Secure loop (the bounded convergence loop in Phase 6), not just Phase 4. It pauses only to **escalate** a stuck loop (cap reached), or at the **final commit/push approval** (the end of Gate 6). Externalize each sub-issue's outcome to its Task so `/resume-reppit` can continue if the session ends.

> **Autonomous flow, in one line:** Gate 3 "Run autonomously" → implement all sub-issues → Test → Secure, looping Implement→Test→Secure on any FAIL (cap 3) — **no stops at Gates 4 or 5** — halting only on escalation or the final "ready to commit & push?" approval. The Test and Secure phases always **run** and still **block on findings**; only the intermediate "shall I proceed?" prompts auto-advance.

**Gate 4 — Implementation Review (review mode only; per sub-issue):**
- Ask: "Sub-issue implemented. Commit and move to next?"
- If the user gives feedback → refine and present again. Loop until OK.
- If OK → commit, move to next sub-issue.
- **In autonomous mode this gate is skipped** — the workflow commits and continues on its own through Test and Secure, stopping only on escalation or at the final commit/push approval (end of Gate 6).

## Phase 5 — Test

After all sub-issues are implemented, follow `${CLAUDE_PLUGIN_ROOT}/commands/review-code.md` to review all changes.

**Gate 5 — Test Review:**
- If review has action items → fix them and re-review. Loop until clean. (This fix loop runs in both modes.)
- **Review mode:** when clean, ask "All tests and review passed. Proceed to security check?" → on OK, proceed to Phase 6.
- **Autonomous mode:** do **not** stop here — once the review is clean, proceed automatically to Phase 6. (Secure always runs regardless of mode, so there is no safety value in pausing to ask permission to run it.)

## Phase 6 — Secure

Follow `${CLAUDE_PLUGIN_ROOT}/commands/secure.md` to run security checks against all changes, for the **enabled frameworks** (any of HIPAA, HITRUST, ISO 27001, SOC 2 — configured via `.claude/reppit-frameworks.json`; see `${CLAUDE_PLUGIN_ROOT}/compliance/frameworks.md`).

**Gate 6 — Security Review:**
- If there are FAIL items, run the **bounded autonomous convergence loop** (no gate between iterations — this is the one place the workflow self-drives):
  1. Implement the security fixes (back to Implement phase logic)
  2. Re-run Test (Phase 5) to verify fixes don't break anything
  3. Re-run Secure to check again
  4. Repeat this Implement → Test → Secure loop until no FAIL items remain **or** the iteration cap is reached.
  - **Iteration cap: 3.** If FAILs remain after 3 full iterations, **escalate**: stop the loop, summarize the remaining FAILs, the fixes attempted each iteration, and why they didn't converge — then hand control back to the user. **Never** silently commit or push past unresolved FAILs.
  - On long-running loops, externalize progress after each iteration (write the iteration outcome to the plan/Tasks) so a resumed session can continue, and self-pace rather than blocking on a human tick.
- WARN items: collect them and surface them at the final approval below (in autonomous mode, don't stop mid-loop for each WARN — carry them to the commit/push checkpoint).
- **Final commit/push approval — this stop happens in _both_ modes** (autonomous mode does not bypass it; you never auto-push). When clean (or warnings acknowledged), ask: "Security check passed. Ready to commit and push?"
- If OK → commit all changes; mark the work done in your tracker — update Linear issues to Done if Linear is available, and mark the corresponding Claude Code Tasks `completed`.
- Play notification sound, then ask: "What branch name?" and offer to create a PR.

## Running unattended

Autonomous mode (chosen at Gate 3) means the workflow stops *asking* between sub-issues — but the turns still come from whatever is **driving** the session. reppit-health is a set of instructions; it does not spawn its own process. So:

- **Interactive Claude Code (the common case):** autonomous mode runs hands-off *within the open session* — you aren't prompted between sub-issues, but the session must stay open and the agent keeps taking turns until it reaches the next gate.
- **Truly unattended (closed laptop, overnight, CI):** drive `/reppit … --autonomous` with an external runner that re-invokes the model — `/loop`, a scheduled cloud agent, or an Agent SDK harness. The plugin defines the *behavior*; the runner supplies the *turns*.

In every case the per-sub-issue bounded loop (cap 3 → escalate) and the mandatory Secure gate bound how far the workflow can go without a human.

## Rules
- **Gates follow the Phase 0 tier policy.** By default every gate is active (wait for explicit user approval before advancing). Only the trivial tier with `--auto` may collapse the early review gates, and `--manual` forces all gates. The **Secure phase and Gate 6 are never skipped for any tier**, and **sensitive tier never auto-advances**.
- **Autonomous mode** is chosen at Gate 3 (or pre-selected with `--autonomous`). It skips the Implement (Gate 4) and Test (Gate 5) review prompts so the workflow self-drives the whole **Implement → Test → Secure** loop (Phases 4–6) — not just Phase 4. Test and Secure still run and block on findings; the only stops are an escalated stuck loop (cap 3) and the **final commit/push approval**, which never auto-advances in any mode. See "Running unattended" for how turns are supplied.
- The Phase 6 convergence loop self-drives between iterations, bounded (cap 3) and escalating to the user — it never bypasses Gate 6's final approval.
- **At every active gate**, before asking the user a question, run `afplay /System/Library/Sounds/Glass.aiff &` to play a notification sound so the user knows input is needed.
- Apply the token-discipline conventions in `${CLAUDE_PLUGIN_ROOT}/commands/token-discipline.md` throughout: delegate heavy reads to subagents and forward only conclusions, pass artifact summaries between phases (re-reading files on demand), and keep stable context stable.
- Keep all context between phases — don't re-read files you already have in context.
- If the user says "stop" or "pause" at any point, halt and summarize current state.
- If the user wants to skip a phase (e.g., "skip research, go straight to plan"), that's allowed — just confirm and jump ahead.
