# Loobster

```
██╗                 ██████╗  ██████╗  ███████╗ ████████╗ ███████╗ ██████╗
██║                ██╔═══██╗ ██╔══██╗ ██╔════╝ ╚══██╔══╝ ██╔════╝ ██╔══██╗
██║       ██████╗  ██║   ██║ ██████╔╝ ███████╗    ██║    █████╗   ██████╔╝
██║      ██╔═══██╗ ██║   ██║ ██╔══██╗ ╚════██║    ██║    ██╔══╝   ██╔══██╗
███████╗ ╚██████╔╝ ╚██████╔╝ ██████╔╝ ███████║    ██║    ███████╗ ██║  ██║
╚══════╝  ╚═════╝   ╚═════╝  ╚═════╝  ╚══════╝    ╚═╝    ╚══════╝ ╚═╝  ╚═╝
          AI that plans, builds, verifies & secures every change — solo or team
```

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8957e5)
![version](https://img.shields.io/badge/version-0.9.4-3fb950)
![tests](https://img.shields.io/badge/tests-45%20passing-3fb950)
![compliance](https://img.shields.io/badge/compliance-4%20frameworks-8957e5)
![security](https://img.shields.io/badge/security-CodeQL-2ea043)

**plan → build → verify → secure · goal-loops · shared signals · configurable compliance · independent verification · local-first**

> 🦞 **Loobster** — loop + lobster. Run [`bin/loobster.sh`](bin/loobster.sh) for the animated red version of the mascot.
>
> 📖 **Docs:** [**nilswidal.github.io/loobster**](https://nilswidal.github.io/loobster/) — a team-focused docs site (source in [`docs/`](docs/), served via GitHub Pages; see [`docs/DEPLOY.md`](docs/DEPLOY.md)).

**Loobster** is a Claude Code plugin that turns AI-assisted development into a **repeatable, reviewable, secure loop**. It right-sizes each task, plans before it builds, can run autonomously between approval gates, and **proves its work with an independent verifier instead of trusting itself**. It coordinates whole teams through a shared signals hub, and runs the compliance frameworks you choose against every diff.

Under the hood it follows the **RePPITS** method — Research, Propose, Plan, Implement, Test, Secure — created by [Mihail Eric](https://github.com/mihail911) ([the RePPIT framework](https://themodernsoftware.dev), from the creator of Stanford's first AI software engineering course). Healthcare (HIPAA/HITRUST) is one aspect, alongside ISO 27001 and SOC 2 — enable only what your repo needs.

## Why loop engineering

AI-assisted development is shifting from one-shot prompts to **durable, autonomous loops** — the *loop*, not the prompt, is becoming the unit of work. An agent that plans, builds, tests, and retries against a goal does far more than one that answers once. The catch: **an unsupervised loop is only as trustworthy as its guardrails.** Left alone, a loop will happily rubber-stamp its own output, drift from scope, or burn the context window.

**Loobster is the harness that makes a loop safe to let run:**
- **Risk-tiered gates** — friction scales with blast radius; sensitive changes never auto-advance.
- **Bounded convergence** — the Implement→Test→Secure fix loop caps at 3 iterations, then escalates to a human (no infinite loops, no silent commits past failures).
- **Never self-verify** — every check runs in a *separate* verifier agent, so a loop can't grade its own work.
- **Signals** — independent loops (and people) coordinate through a shared, mergeable channel.
- **Compliance + token discipline** — gates run against the diff; context stays lean enough that long loops stay affordable.

It stands on two foundations: **[RePPIT](https://themodernsoftware.dev)** (Mihail Eric) gives the phase structure a loop iterates over, and **[headroom](https://github.com/headroomlabs-ai/headroom)** (Tejas Chopra) gives the token economics that make long loops viable. Loobster wires both into the agent's control loop.

## At a glance

| Capability | What it does |
|---|---|
| **Structured workflow** | Research → Propose → Plan → Implement → Test → Secure (the RePPITS method), with explicit approval gates |
| **Adaptive gating** | Phase-0 right-sizing (trivial / standard / sensitive) chooses which gates apply; sensitive never auto-advances |
| **Autonomous mode** | At Gate 3, "run autonomously" drives Implement → Test → Secure on its own (bounded loop, cap 3, escalate; final commit/push always stops) |
| **Goal-loop** | `/loop` works a prioritized RICE-scored backlog toward a standing goal, cycle after cycle — **crash-safe** (reclaims interrupted tasks) and runs to a real exit condition, never pausing at a milestone |
| **Signals hub** | `/signals` — a shared team hub: any loop/teammate emits observations, any loop consumes them, with a dynamic dashboard |
| **Configurable compliance** | Enable any of **HIPAA · HITRUST · ISO 27001 · SOC 2** per repo — healthcare is a profile, not a requirement |
| **Token discipline** | Subagent isolation + artifact compaction always on; optional [headroom](https://github.com/headroomlabs-ai/headroom) compression |

## What you get

Eleven slash commands, available in Claude Code, Cursor, **Codex**, and any client that supports the Claude Code plugin spec or the `AGENTS.md` / `.agents/skills` convention (two shared reference docs — `backlog-scoring` and `token-discipline` — live in `reference/`, not as commands):

| Command | What it does |
|---|---|
| `/run <topic-or-issue>` | Run the full Research → Propose → Plan → Implement → Test → Secure workflow, with explicit approval gates between phases |
| `/loop <goal>` | Run a continuous goal-loop: work down a prioritized backlog toward a standing goal, learning each cycle (wraps `/run` as its "act" step) |
| `/signals` | Shared signals hub: any loop/teammate emits observations to a committed `signals/` store, any loop consumes the relevant ones (team coordination on one codebase) |
| `/verify-frontend` | Verifiable frontend layer: when a change touches the UI, capture Playwright screenshots and attach them to the PR (GitHub-native, no other accounts) |
| `/research-codebase` | Document the existing codebase exactly as it is today (no suggestions, no RCA) |
| `/make-proposals` | Generate up to two solution proposals grounded in research |
| `/make-plan` | Break the chosen proposal into ordered Linear issues (or local `plans/*.md` if Linear MCP is not configured) |
| `/implement <issue>` | Implement a single Linear issue (optionally inside the built-in bounded autonomous loop via `--autonomous`) |
| `/review-code` | Review all uncommitted changes, post findings to Linear |
| `/secure` | Run your enabled checklists (any of HIPAA, HITRUST, ISO 27001, SOC 2) against your diff, separating code-verifiable findings from organizational controls |
| `/resume` | Resume a paused, interrupted, or crashed workflow by reconstructing state from Claude Code Tasks |

```mermaid
flowchart LR
    Start([Topic or Issue]) --> RS{{"Right-size<br/>trivial · standard · sensitive"}}
    RS --> R

    subgraph G["Gated · refine until approved"]
        direction LR
        R[Research] --> P[Propose] --> PL[Plan]
    end

    subgraph A["Autonomous fix loop · ≤3 then escalate"]
        direction LR
        I[Implement] --> T[Test] --> S[Secure]
        S -.->|FAIL| I
    end

    PL --> I
    S --> Done([Done · commit · PR])

    classDef phase fill:#1f6feb,stroke:#0d419d,color:#fff;
    classDef gate  fill:#8957e5,stroke:#6e40c9,color:#fff;
    classDef term  fill:#238636,stroke:#1a7f37,color:#fff;
    class R,P,PL,I,T,S phase
    class RS gate
    class Start,Done term
```

## Adaptive, autonomous, dynamic

The workflow adapts to the task instead of forcing every change through identical friction:

- **Right-sizing (Phase 0).** `/run` classifies each task **trivial / standard / sensitive** and picks a gate policy. Trivial tasks can auto-advance the early phases with `--auto`; **sensitive tasks (PHI, auth, encryption, audit, multi-tenant, infra) never auto-advance**, and the **Secure phase always runs for every tier**. `--manual` forces every gate.
- **Autonomous convergence loop.** When Secure finds FAILs, the Implement→Test→Secure fix loop self-drives (no gate between iterations) up to a **cap of 3**, then escalates to a human — it never silently commits past unresolved FAILs.
- **Capability tiers.** The same workflow degrades gracefully across runtimes: Tier 0 (always-on, markdown-only) → Tier 1 (parallel independent sub-issues via subagents) → Tier 2 (deterministic Workflow harness, opt-in; tracked as a follow-up).
- **Resumable.** Plan-phase work is recorded as Claude Code Tasks with a real status lifecycle, so `/resume` can rebuild and continue after a crash or a new session.
- **Self-healing, self-driving loops.** `/loobster:loop <goal>` arms its **own** durable re-entry (a `ScheduleWakeup`/cron that re-invokes itself) — no need to wrap it in a separate scheduler — and **prints the schedule it armed** on kickoff (cron expression, cadence, job id, how to cancel), just like the `/loop` skill. Ask **`/loobster:loop status`** anytime to see the schedule, backlog, and readiness. It heartbeats each in-progress task and checkpoints every cycle, so a dead turn (API drop, crash, stop) is reclaimed and resumed — not lost. A **single-runner lease** keeps only one instance looping per worktree, so a wakeup/cron re-entry (or a parallel run) **backs off instead of colliding** — self-driving is concurrency-safe via an **atomic lock file** (`bin/loop-lease.py`, claimed with `O_CREAT|O_EXCL`), even on a shared worktree. A bundled Stop hook (`bin/loop-rearm.py`) keeps an active loop from stopping at a milestone, while leaving approval gates (`status: paused`) sacred. `LOOBSTER_LOOP_REARM=0` to disable the hook.

## Token reduction

Loobster keeps the model's working context lean in two layers:

1. **Native token discipline (always on, zero-dependency, portable).** `reference/token-discipline.md` bakes in subagent isolation (heavy reads happen in a subagent; only the conclusion returns), artifact compaction (pass summaries between phases, re-read files on demand), cache-stable prefixes, and terse output. This reduces tokens by *elimination and structure* — it works identically in Claude Code, the plugin, and a custom Agent SDK harness.
2. **Wire-level compression with [headroom](https://github.com/headroomlabs-ai/headroom) (Option D — on by default).** For real, automatic, every-read compression, Loobster ships headroom integration:
   - **Option D — bundled hook (Claude Code context), enabled by default.** The `PostToolUse` hook in `hooks/hooks.json` pipes large tool outputs through a locally-installed headroom — `pip install "headroom-ai[code]"` — via `bin/headroom-compress.py` before they enter context. It's **on by default** and a **no-op when headroom isn't installed**; set `LOOBSTER_HEADROOM=0` to disable — do this on PHI repos until headroom has had a data-path review.
   - **Option C — proxy / SDK middleware (any context, incl. Agent SDK).** Run `headroom proxy` and point your base URL at it, or use headroom's SDK middleware in your own harness.

> **Gratitude & attribution.** The token-reduction design here adapts the mechanisms pioneered by [**headroom** (headroomlabs-ai/headroom)](https://github.com/headroomlabs-ai/headroom) — reversible-context retrieval (CCR), prefix stabilization (CacheAligner), and content-type-aware compression of what the model reads. The native conventions are a runtime-free interpretation of those ideas; Options C/D use headroom itself. Thank you to the headroom authors. A markdown plugin has no wire to intercept, so it cannot *be* a proxy or SDK middleware — replication is per-context (a hook covers Claude Code; middleware/proxy covers the Agent SDK), never universal.
>
> **Healthcare caveat.** Enabling Option D or C puts a compressor in the **PHI data path** (it reads tool outputs that may contain PHI), and headroom's CCR stores originals locally (PHI-at-rest). Option D is on by default but **no-ops unless headroom is installed**; **disable it (`LOOBSTER_HEADROOM=0`) in PHI environments** until a data-path sign-off, and Option C is opt-in — see `compliance/org-controls-audit.md`.

## Goal-loop mode

Where `/run` builds *one thing*, `/loop <goal>` pursues a *standing goal* by working down a prioritized backlog and learning each cycle. It's an **outer loop that wraps `/run`** as its "act" step:

```mermaid
flowchart LR
    Goal([Goal + success criteria]) --> T{{"Trigger<br/>next backlog item"}}
    T --> IA["Investigate &amp; Act<br/>runs /run in a subagent"]
    IA --> BG["Backlog gen / assign<br/>RICE-scored Tasks"]
    BG --> RL["Review &amp; learn<br/>judge vs goal · re-score"]
    RL -->|goal not met| T
    RL -->|met / cap / budget| Done([Done · summary])

    classDef step fill:#1f6feb,stroke:#0d419d,color:#fff;
    classDef gate fill:#8957e5,stroke:#6e40c9,color:#fff;
    classDef term fill:#238636,stroke:#1a7f37,color:#fff;
    class IA,BG,RL step
    class T gate
    class Goal,Done term
```

- **Backlog = Claude Code Tasks + metadata.** Items are scored with a model-set **RICE** estimate (`(reach × impact × confidence) / effort`); the loop always works the highest-scored open item and re-scores each cycle (see `reference/backlog-scoring.md`).
- **Goal = free text, model-judged.** The model judges met / partial / not-met against your free-text success criteria each cycle.
- **Bounded & resumable.** Cycle cap + optional token budget; escalates on a stuck item, a sensitive Secure FAIL, or a budget spike; the backlog is durable so the loop resumes after a crash. Compliance gates and Secure are never bypassed; nothing auto-pushes.
- **Enable compression for loops.** A goal-loop re-reads code every cycle, so we **recommend turning on Option D** (`LOOBSTER_HEADROOM=1`, see Token reduction above) — the repeated code reads are exactly headroom's AST-aware `CodeCompressor` sweet spot.

## Signals hub

A shared **central hub** for teams working on one codebase: any loop, agent, or teammate **emits** observations (frictions / opportunities / facts) into a committed `signals/` store, and any loop **consumes** the relevant ones. It's the decoupled channel that lets independent loops — and people — coordinate.

```mermaid
flowchart LR
    LA["Loop / teammate A"] -->|emit| HUB[("signals/ hub")]
    LB["Loop / teammate B"] -->|emit| HUB
    LC["one-off agent / human"] -->|emit| HUB
    HUB -->|consume relevant| LA
    HUB -->|consume relevant| LD["Loop D"]
    HUB -.build.-> DASH["dashboard<br/>+ Pages (optional)"]
    classDef loop fill:#1f6feb,stroke:#0d419d,color:#fff;
    classDef hub fill:#8957e5,stroke:#6e40c9,color:#fff;
    classDef out fill:#238636,stroke:#1a7f37,color:#fff;
    class LA,LB,LC,LD loop
    class HUB hub
    class DASH out
```

- **One signal = one file** — `signals/<date>-<author>-<slug>.md` (frontmatter + 1-line body). File-per-signal keeps multi-writer merge conflicts rare; `author` gives team attribution. See `commands/signals.md`.
- **Committed + shared** — the hub is tracked so the whole team sees it. The **load-bearing rule: signals are non-PHI summaries** ("5 users asked about export", never raw PHI) — `/secure` checks it with `bin/signals-build.py --strict`, a best-effort PHI lint that **quarantines** flagged signals from the build by default (a lint, not a guarantee).
- **Dynamic dashboard** — `bin/signals-build.py` regenerates `signals/{data.js,data.json,INDEX.md}`; open `templates/signals-dashboard.html` for a live team-status board (group by status / author / loop / type; auto-refresh).
- **Optional GitHub Pages** — `templates/signals-pages.yml` publishes the dashboard to a shared team URL, updated on each push. **Private repo / non-PHI only** (a public Pages site would expose your signals) — see `compliance/org-controls-audit.md`.
- **Signals are upstream of the backlog** — consuming a signal can spawn a RICE-scored `/loop` task.

## Use with Codex

Loobster isn't Claude-Code-only. The same workflow ships in two cross-tool formats, generated from the canonical `commands/*.md`:

- **[`AGENTS.md`](AGENTS.md)** — the methodology + non-negotiable rules, read automatically by **Codex** (and any `AGENTS.md`-aware agent) from the repo root.
- **[`.agents/skills/`](.agents/skills/)** — each command as a Codex **skill** (`<name>/SKILL.md`), invoked with `/skills` / `$run` or implicitly. (Codex deprecated custom prompts in favor of skills; these are the skills.)

```bash
# from a repo that has Loobster's AGENTS.md + .agents/skills/ present:
codex            # then:  $run <task>   ·   $loop <goal>   ·   $secure
```

**headroom on Codex:** Codex has no PostToolUse hook, so use headroom's **proxy/middleware (Option C)** — run `headroom proxy` and point Codex's model base URL at it. (The bundled Option-D hook is Claude-Code-specific.)

Regenerate the skills after editing a command: `python3 bin/build-codex-skills.py` (`--check` in CI flags drift).

## Install

### From the plugin marketplace (recommended)

In Claude Code (≥ 1.0.33):

```
/plugin marketplace add NilsWidal/loobster
/plugin install loobster@nilswidal-loobster
```

That's it. The slash commands are immediately available.

### From a local clone

```bash
git clone https://github.com/NilsWidal/loobster.git
```

Then in Claude Code:

```
/plugin marketplace add ./loobster
/plugin install loobster@nilswidal-loobster
```

Useful for trying changes before pushing.

## Quick start

In any project directory:

```
/run Add a patient intake form
```

or with a Linear issue:

```
/run CAR-123
```

The plugin walks Research → Propose → Plan → Implement → Test → Secure and pauses at each gate for your approval. You can also invoke any phase directly, e.g. `/secure` to audit current uncommitted changes without running the full flow.

## Compliance checklists — pick your frameworks

Compliance is **configurable**: enable any of four frameworks per repo. Healthcare is one aspect, not a requirement. Checklists live in `compliance/` inside the installed plugin:

- **`hipaa-checklist.md`** — Administrative, physical, and technical safeguards (§164.308-312), PHI detection, minimum necessary, BAA verification, breach notification, telehealth compliance
- **`hitrust-checklist.md`** — All 14 CSF v11 control categories (00-13): access control, risk management, encryption, operations, incident management, business continuity, privacy practices, cross-tenant isolation
- **`iso27001-checklist.md`** — ISO/IEC 27001:2022 Annex A controls relevant to a code diff: secure development (A.8.25-28), cryptography, access control, logging & masking, vulnerability & config management
- **`soc2-checklist.md`** — All Trust Service Criteria (CC1-CC9), Availability (A1), Confidentiality (C1), Processing Integrity (PI1), Privacy (P1), plus injection prevention and secrets management
- **`org-controls-audit.md`** — Schedule and tracking for organizational controls that can't be verified from code alone

Each item gets a PASS / WARN / FAIL / SKIPPED status. Items marked `[org]` (physical safeguards, board oversight, BAAs with subprocessors) are surfaced separately so they don't get auto-passed by a green diff.

### Enable / disable frameworks

Drop `.claude/loobster-frameworks.json` in your repo to choose which run:

```json
{ "frameworks": ["soc2", "iso27001"] }
```

`/secure` runs only the listed frameworks; with no file, the default is **all four**. Suggested profiles — healthcare: `["hipaa","hitrust","soc2"]` · general SaaS: `["soc2","iso27001"]`. See `compliance/frameworks.md`.

### Per-workspace overrides

To customize a checklist for a specific repo, drop a file at `.claude/compliance/<framework>-checklist.md` in that workspace. `/secure` reads workspace overrides first, then falls back to the plugin's defaults.

## Linear integration (optional)

If the [Linear MCP](https://linear.app/docs/mcp) is configured in Claude Code, the plugin will:

- Read issues mentioned in `/implement <issue-id>`
- Save research and proposal documents as Linear documents
- Create parent + sub-issue structures during `/make-plan`
- Post review and security findings as comments on the relevant issue

If Linear is not configured, the plugin falls back to local `.md` files in `research/`, `plans/`, and the conversation transcript. Both modes work end-to-end.

## Credits

- **RePPIT methodology** — [Mihail Eric](https://github.com/mihail911), Head of AI, creator of [Stanford's first AI software engineering course](https://themodernsoftware.dev)
- **Token-reduction mechanisms** — [headroom](https://github.com/headroomlabs-ai/headroom) by [Tejas Chopra](https://github.com/chopratejas), whose CCR, CacheAligner, and content-type compressors inspired the native token-discipline conventions and power the optional Option C/D integrations
- **Loobster** — by [Nils Widal](https://github.com/NilsWidal)

## License

Apache 2.0, see [LICENSE](LICENSE).
