# Design Doc: Autonomous Loops & Dynamic Workflows for reppit-health (Proposal 3 Hybrid + Option D)

## Context
reppit-health is a pure-markdown prompt-orchestration plugin. Today its workflow is strictly linear, synchronous, single-agent, and fully human-gated (`reppit.md:80` "NEVER skip a gate"); every loop is a human refinement loop; sub-issues run serially; there is no right-sizing, no subagent fan-out, no background/scheduling, write-only `TaskCreate`, and a dangling external `ralph-loop` reference. We want more autonomy (self-driving where safe) and dynamism (task-shaped control flow), plus headroom-grade token reduction where the runtime allows it — without breaking the plugin's portability across Claude Code CLI, the plugin, and custom Agent SDK harnesses.

See research: `research/autonomous-loops-dynamic-workflows.md`. See proposals: `research/proposals-autonomous-loops.md`.

## Requirements
- [ ] **Adaptive gating** — classify task risk/complexity (trivial/standard/sensitive) and select which gates apply; *sensitive (PHI/auth/infra) always keeps full gates + mandatory Secure*; global `--manual` override.
- [ ] **Autonomous convergence loop** — bounded Implement→Test→Secure loop (cap + escalate), self-pacing on long runs.
- [ ] **Real Tasks lifecycle** — `TaskUpdate`/`TaskList` across implement/review/secure; `/resume-reppit` rebuilds state from `TaskList`.
- [ ] **Native token discipline (Option A)** — subagent isolation for heavy reads, artifact-compaction (summary-forward + re-read on demand), cache-stable prefixes. Always on, portable.
- [ ] **Tier 1 parallelism** — fan-out research; implement independent (non-blocking) sub-issues concurrently.
- [ ] **Tier 2 Workflow harness** — deterministic orchestration when the `Workflow` tool is available AND user opts in; degrades to Tier 1/0.
- [ ] **Option D — headroom-grade compression hook** — opt-in, default-OFF `PostToolUse` hook that pipes tool output through a locally-installed headroom (`updatedToolOutput`) when enabled+present, else passes through unchanged.
- [ ] **Attribution** — README gratitude + credit to headroom (chopratejas/headroom) for the mechanisms (CCR, CacheAligner, content-type compressors).
- Non-functional: no build step (text + small bin script); portable (Tier-0 works on any plugin-spec client); compliance posture must *improve*, never regress; nothing puts a compressor in the PHI path by default.

## Research Summary
- reppit-health is markdown-only; control flow is advisory prose (`research/...autonomous-loops...md` §1).
- All loops human-gated (§2); ralph dangling external (§3); Tasks write-only (§4); no parallelism/background/scheduling/routing (§5); extension surface supports new commands/`agents/`/`hooks/`/`bin/` (§6).
- Verified: a plugin `PostToolUse` hook **can** rewrite tool output via `updatedToolOutput`; plugins ship `hooks/hooks.json`, `.mcp.json`, and `bin/` executables (any language). A hook only fires in the Claude Code context — not in a bare Agent SDK app — so headroom replication is per-context, never universal.

## Chosen Approach
**Proposal 3 (Hybrid), Option A native + Option D opt-in.** A capability ladder: Tier 0 (P1 adaptive gates + autonomous loop + Tasks + native token discipline, always-on, portable) → Tier 1 (subagent parallelism) → Tier 2 (Workflow harness, opt-in). Token reduction = Option A always-on + Option D as an opt-in, default-off, security-reviewed `PostToolUse` hook that *uses* headroom rather than reimplementing it (honoring the "use their mechanisms with gratitude" intent). Option C (proxy/SDK middleware) documented as the path for the Agent SDK context.

## Design

### Architecture
Orchestrator (`reppit.md`) gains a Phase 0 that picks a **tier = f(risk-size, available-runtime, opt-in)**. Commands carry native token-discipline conventions. Option D lives entirely in `hooks/` + `bin/`, gated by config and capability detection, default OFF.

### Key Changes
| Component | Change | Notes |
|-----------|--------|-------|
| `commands/reppit.md` | Phase 0 right-sizing + tier table; bounded convergence loop; ralph fallback; parallel sub-issue routing; Tier-2 escalation | Largest single edit |
| `commands/research-codebase.md`, `review-code.md`, `secure.md` | Delegate heavy reads to `Agent`/`Explore`; forward conclusions only; `TaskUpdate` lifecycle | Option A + Tasks |
| `commands/implement.md`, `make-plan.md` | `TaskUpdate` lifecycle; mark sub-issue independence for parallelism | |
| `commands/resume-reppit.md` (new) | Rebuild state from `TaskList`, continue from last incomplete task | New command |
| `commands/token-discipline.md` (new) | Shared Option-A conventions referenced by other commands | New doc |
| `agents/*.md` (new) | Specialized subagents for Tier-2 harness | Tier 2 |
| `commands/reppit-orchestrate.md` (new) | Tier-2 Workflow-tool harness launcher | Tier 2, opt-in |
| `hooks/hooks.json` + `bin/headroom-compress.*` (new) | Option D PostToolUse compression hook, default OFF | Opt-in; PHI-path caveat |
| `.claude-plugin/plugin.json`, `marketplace.json` | Declare hooks; version bump; keywords | |
| `README.md`, `CHANGELOG.md`, `compliance/*` | Attribution/gratitude; tier docs; PHI-path note for Option D | |

### Data Model
None (markdown plugin). Claude Code Tasks are the only state store; Option D may use headroom's local CCR store (originals on disk) — treated as PHI-at-rest when enabled.

### API Changes
New slash commands `/resume-reppit`, `/reppit-orchestrate`. New hook event wired (PostToolUse). No external API.

## Security Considerations
- **Adaptive gating must not weaken compliance:** sensitive tier (PHI/auth/infra touch) always runs full gates + mandatory Secure; `--manual` forces all gates.
- **Option D is in the PHI data path when enabled:** default OFF; passthrough when headroom absent; document that enabling routes tool outputs (possible PHI) through the compressor; CCR originals = PHI-at-rest (encryption/GC/BAA per org policy). Add to compliance docs.
- Autonomous loop must escalate-to-human on cap, never silently push.

## Testing Plan
- Repo has **no test harness** — add lightweight fixtures: 3 dry-run task descriptions (trivial / standard / PHI-sensitive) and assert the tier→gate-policy mapping; assert sensitive never auto-advances.
- `/resume-reppit`: kill mid-run, confirm rebuild from `TaskList`.
- Option D: hook returns `updatedToolOutput` when headroom present+enabled; passthrough when absent; OFF by default.
- ralph fallback path runs when `/ralph-loop:ralph-loop` absent.
- Each slice: `/review-code` + `/secure` against the diff (this is reppit running on itself).

## Rollout
- Ship in slice order (below); Tier-0 first delivers value standalone.
- Option D ships disabled; enabling is a documented opt-in.
- Rollback: each slice is one commit; revert independently. No migrations.

## Slices (ordered, one commit each)
1. **Tier-0 orchestrator** — `reppit.md`: Phase 0 right-sizing + tier table + bounded convergence loop + ralph fallback + `--manual`.
2. **Tasks lifecycle + resume** — `TaskUpdate`/`TaskList` in implement/review/secure; new `resume-reppit.md`.
3. **Option A native token discipline** — new `token-discipline.md`; subagent-isolation + artifact-compaction edits to research/review/secure; reference from `reppit.md`.
4. **Tier-1 parallel sub-issues** — `reppit.md` Phase 4 + `make-plan.md` independence marking + concurrent `Agent`/worktree implement.
5. **Tier-2 Workflow harness** — `agents/*.md` + `reppit-orchestrate.md`, capability-gated + opt-in. *(Heaviest; can split to a follow-up.)*
6. **Option D headroom hook** — `hooks/hooks.json` + `bin/headroom-compress.*`, default OFF, capability-detect headroom, PHI-safe passthrough.
7. **Docs & manifest** — README gratitude/attribution to headroom + tier docs; CHANGELOG; `plugin.json`/`marketplace.json` hooks + version + keywords; compliance PHI-path note.

Dependencies: 1 → 2,3,4; 4 → 1; 5 → 1,3,4; 6 independent; 7 → all.

## Decisions (Gate 3)
- **Trivial-tier auto-advance:** opt-in via `--auto` only. Trivial tasks still hit gates by default (compliance-conservative).
- **Tier-2 Workflow harness (slice 5):** DEFERRED to a follow-up epic. This round implements slices **1, 2, 3, 4, 6, 7**.
- **Plan location:** local `plans/` + Claude Code Tasks. Not mirrored to Linear.
- Convergence-loop cap: default **3** iterations, then escalate = stop + summarize state (no silent push).

## Deferred follow-up epic — Tier-2 Workflow harness
`agents/*.md` (reppit-researcher/implementer/reviewer/secure-auditor) + `commands/reppit-orchestrate.md`: a capability-gated, opt-in Workflow-tool harness (pipelined phases, worktree-parallel sub-issues, loop-until-dry Secure, adversarial FAIL verification) that degrades to Tier 1/0. Tracked here; not built this round.
