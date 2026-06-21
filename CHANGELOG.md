# Changelog

## 0.6.0 — Configurable compliance frameworks (health is one aspect) + clearer README

- **Frameworks are now enable/disable** per repo via `.claude/loobster-frameworks.json` (`{ "frameworks": ["soc2","iso27001"] }`); `/secure` runs only the enabled ones, defaulting to all four when no config is present. Healthcare (HIPAA/HITRUST) is positioned as **one profile**, not a requirement. See `compliance/frameworks.md`.
- **New ISO/IEC 27001:2022 checklist** (`compliance/iso27001-checklist.md`) — Annex A controls relevant to a code diff (secure development, cryptography, access control, logging/masking, vulnerability/config management) + built-in fallback checks in `/secure`.
- `secure.md` is now framework-agnostic: reads the enabled set, runs one section per enabled framework, and the report lists which frameworks ran.
- **README rewritten for clarity/visibility** — an "At a glance" capability table surfaces adaptive gating, autonomous mode, the goal-loop, the signals hub, configurable compliance, and token discipline up front; repositioned from "healthcare software" to a secure autonomous dev workflow where healthcare is one aspect.
- Supported frameworks: **HIPAA · HITRUST · ISO 27001 · SOC 2**. Sample config at `compliance/loobster-frameworks.example.json`.
- Bump to 0.6.0; add `iso27001` / `frameworks` keywords. (Repo/plugin rename to a general name is tracked as a follow-up — a GitHub repo rename preserves stars + sets up redirects; the plugin `name` is unchanged here to avoid breaking existing installs.)
- **Never self-verify (new core rule):** every verification/review/judgment step (Test, Secure, frontend verify, the loop's verify) MUST run in a **separate verifier subagent** that did not produce the work. Wired into `run.md`, `review-code.md`, `secure.md`, `loop.md`, `verify-frontend.md`.
- **Verifiable frontend layer:** new `/verify-frontend` — when a change touches the UI, capture Playwright screenshots (`bin/screenshot.mjs`, blocks on 4xx/5xx or console errors) and attach them to the PR **GitHub-native, no other accounts** (Actions artifacts via `templates/playwright-verify.yml` + a native PR comment; or committed-to-branch images embedded via raw URLs). Wired into the Test phase.
- **Loobster** 🦞 — loop + lobster mascot. Animated red ASCII via `bin/loobster.sh`; static version in the README.
- **Rebranded to Loobster** — new ASCII "LoOBSTER" logo (lowercase-o motif), repo moving to `github.com/NilsWidal/loobster` (a GitHub transfer preserves the 23 stars + redirects), plugin/marketplace names → `loobster` / `nilswidal-loobster`, category → developer-tools. Plugin author still credits Cara.
- **Docs site** — a team-focused static docs site in `site/` (Vercel-deployable for a shared URL); see `site/DEPLOY.md`.

## 0.5.0 — Signals hub (team coordination) + dynamic dashboard

- **New `/signals` — a shared central hub** for multi-person teams on one codebase: any loop/agent/teammate **emits** observations (friction/opportunity/fact) to a committed `signals/<date>-<author>-<slug>.md` store, and any loop **consumes** the relevant ones. File-per-signal = merge-safe for multiple writers; `author` gives attribution; cross-author dedup; lifecycle `new→ack→acted→archived`.
- **Loop integration** — `/loop` now consumes relevant signals in its Trigger step and emits signals in Review & learn; a consumed signal can spawn a RICE-scored backlog task.
- **Dynamic team dashboard** — `bin/signals-build.py` regenerates `signals/{data.js,data.json,INDEX.md}` from the signal files; `templates/signals-dashboard.html` renders a live status board (group by status/author/loop/type, auto-refresh, works from `file://` and when served). Tests in `tests/test-signals-build.sh`.
- **Optional GitHub Pages** — `templates/signals-pages.yml` publishes the dashboard to a shared team URL on each push. **Private repo / non-PHI only.**
- **Compliance** — the load-bearing rule is **no PHI in shared signals** (committed + shared); `/secure` enforces it (`signals-build.py --strict`), and `compliance/org-controls-audit.md` adds a signals + Pages data-path control.
- Bump to 0.5.0; add `signals`/`team` keywords; `/signals` added to the command list.

## 0.4.2 — Loop permission prompts: docs + safer subagent defaults

- **Documented the real cause of mid-loop permission prompts:** subagents do **not** inherit a session's runtime `--dangerously-skip-permissions`; they resolve mode from settings, and `defaultMode: "auto"` makes the classifier evaluate each subagent's tool calls — so you get write prompts even when the main session shows bypass. Fix: set `permissions.defaultMode: "bypassPermissions"` (a launch flag alone isn't enough for subagents) plus a `deny` guardrail list.
- **`/loop`:** new "Permissions" section; the act step no longer forces `isolation: "worktree"` (worktrees write to untrusted paths and trigger prompts under non-bypass modes) — worktree isolation is now reserved for genuine parallelism under bypass.
- **`/run` Phase 4:** added the same permission caveat to the parallel/worktree sub-issue guidance.

## 0.4.1 — Rename to /loop + make the loop concretely runnable

- **Renamed the dedicated loop command to `/loop`**. Invoke it namespaced: **`/loobster:loop <goal>`** (the bare `/loop` only resolves if aliased as a project command).
- **Made the command executable, not advisory:** it now spells out the concrete tool calls (`TaskCreate` the goal + backlog, `TaskList`→pick→`Agent`→act→`TaskUpdate`, re-score) and **runs cycles back-to-back in-session** — it no longer stops after one item. Added a clear "How to run it (so it actually loops)" section, including wrapping with `/loop` or a scheduled agent for unattended/persistent runs.
- Goal record + learnings now persist under `plans/loop/<slug>.md`; backlog stays in Claude Code Tasks.

## 0.4.0 — Goal-loop mode (dedicated loops & goals + optimizable backlog)

- **New `/loop <goal>` command:** a continuous goal-loop — Trigger (next backlog item) → Investigate & Act (runs `/run` in an isolated subagent) → Backlog gen/assign → Review & learn → ↺ — until the goal is met, the cycle cap is hit, or budget is exhausted. Wraps RePPITS as its "act" step; never bypasses gates/Secure; never auto-pushes; resumable from the backlog.
- **Optimizable backlog = Claude Code Tasks + metadata.** New `commands/backlog-scoring.md` defines a **model-set RICE** score (`(reach × impact × confidence) / effort`) stored in each Task's `metadata`; the loop works the highest-scored open item and re-scores each cycle. `/make-plan` tags sub-tasks with the `goalId` + RICE when run under a goal.
- **Goal = free text, model-judged** (met / partial / not-met against free-text success criteria).
- **Token economics for loops:** per-cycle subagent isolation + artifact-compacted backlog/learnings (always on), a per-cycle budget guard, and a **hard recommendation to enable Option D headroom AST compression** (`LOOBSTER_HEADROOM=1`) — a loop's repeated code reads are headroom's `CodeCompressor` (AST) sweet spot.
- README: new "Goal-loop mode" section with a rendered Mermaid loop diagram.

## 0.3.2 — Autonomous mode spans the full loop (4→6)

- **Fix:** autonomous mode now drives the whole **Implement → Test → Secure** loop (Phases 4–6), not just Phase 4. Previously it halted at Gate 5 ("Proceed to security check?"), so the loop only ran within implementation.
- Autonomous mode now **auto-advances the Implement (Gate 4) and Test (Gate 5) review prompts** for every tier; the Test and Secure phases still **run and block on findings**, and the **final commit/push approval always stops** (never auto-pushes).
- Clarified that the per-tier `--auto` policy and **autonomous mode** are orthogonal mechanisms, and removed the contradictory "autonomous still stops at Gate 5" wording across Arguments, Gate 3, Gate 4/5/6, and Rules. WARN items are now carried to the final approval rather than interrupting the loop.

## 0.3.1 — Autonomous kickoff & docs

- **Explicit autonomous kickoff at Gate 3:** after the plan is approved you now choose **(a) run autonomously**, **(b) step through each sub-issue**, or **(c) make changes**. "Run autonomously" is what hands control to the workflow to drive Implement → Test → Secure on its own — resolving the previously underspecified hand-off after planning.
- **Defined autonomous mode precisely** and fixed a contradiction: in autonomous mode the per-sub-issue Gate 4 is skipped (workflow commits and continues), the bounded loop (cap 3) still escalates on failure, and Gate 5/6 still stop — sensitive tier never skips Test/Secure.
- **New "Running unattended" section** in `/run`: clarifies that the plugin defines behavior but the *turns* come from a driver — interactive Claude Code (hands-off in-session), or `/loop`/scheduled agent/Agent SDK for truly unattended runs.
- **README workflow diagram** is now a rendered Mermaid flowchart (replacing the ASCII art), showing the gated and autonomous-fix-loop bands.

## 0.3.0 — Autonomous loops & dynamic workflows

- **Adaptive gating (Phase 0):** `/run` now right-sizes each task (trivial / standard / sensitive) and applies a gate policy per tier. New `--auto` (let trivial tasks auto-advance early phases) and `--manual` (force all gates) flags. Sensitive tasks never auto-advance; the Secure phase always runs for every tier.
- **Bounded autonomous convergence loop:** the Implement→Test→Secure fix loop self-drives up to 3 iterations, then escalates to a human — never silently commits past unresolved FAILs.
- **Resumable workflows:** real Claude Code Tasks status lifecycle across Implement/Test/Secure, plus a new `/resume` command that rebuilds state from `TaskList` after a crash or new session.
- **Tier-1 parallelism:** independent sub-issues (disjoint files, no blocking edge) are implemented concurrently in isolated worktrees via subagents; degrades to serial when subagents aren't available.
- **Built-in autonomous implementation loop:** removed the external `/ralph-loop` dependency in favor of a first-party `--autonomous` flag that implements sub-issues in the built-in bounded loop (iterate implement→test until acceptance criteria pass, cap 3, then escalate) — no external plugin required.
- **Native token discipline (Option A):** new `commands/token-discipline.md` — subagent isolation, artifact compaction, cache-stable prefixes, terse output. Always on, zero-dependency, portable.
- **Optional headroom compression (Option D):** opt-in, default-OFF `PostToolUse` hook (`hooks/hooks.json` + `bin/headroom-compress.py`) that compresses large tool outputs via a locally-installed [headroom](https://github.com/chopratejas/headroom) when `LOOBSTER_HEADROOM=1`. Graceful passthrough otherwise. Tests in `tests/test-headroom-hook.sh`. Healthcare PHI-data-path caveat documented in the README and `compliance/org-controls-audit.md`.
- Tier-2 deterministic Workflow harness (subagents + Workflow-tool orchestration) is designed and tracked as a follow-up epic in `plans/autonomous-loops/`.

## 0.2.0 — Plugin pivot

- Repackaged as a Claude Code plugin (was a VS Code / Cursor extension)
- Installable via `/plugin marketplace add NilsWidal/loobster`
- Seven slash commands: `/run`, `/research-codebase`, `/make-proposals`, `/make-plan`, `/implement`, `/review-code`, `/secure`
- Cross-references inside commands use `${CLAUDE_PLUGIN_ROOT}` for plugin-local paths, with `.claude/compliance/*.md` workspace overrides supported by `/secure`
- Extension scaffold (`src/`, `dist/`, `package.json`, VSIX, sidebar webview) removed; full history preserved at the `pre-plugin-pivot` git tag

## 0.1.0 — Initial Release (VS Code / Cursor extension, archived)

- Full RePPITS workflow: Research, Propose, Plan, Implement, Test, Secure
- Visual sidebar with phase stepper, gate prompts, and real-time log
- HIPAA, SOC2, and HITRUST compliance checklists with pass/warn/fail reporting
- Sound and system notifications at workflow gates
- Optional Linear integration (auto-detected via MCP, falls back to local .md files)
- Scaffoldable command templates (`RePPIT: Initialize Project Templates`)
- Standalone `/secure` command for ad-hoc security checks
- Works in VS Code and Cursor
