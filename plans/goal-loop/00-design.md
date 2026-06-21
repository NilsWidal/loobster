# Design: RePPIT Goal-Loop (dedicated loops & goals + optimizable backlog)

**Date:** 2026-06-21
**Status:** design for review (build not started)

## Context
Today reppit-health is a **one-shot, gated pipeline** (RePPITS: Research→…→Secure→Done) that builds one thing. The requested pattern is a **continuous goal-loop**:

```
Trigger → Investigate & Act → Backlog gen / Assign task → Review & learn → ↺
```

This is an **outer loop** that *wraps* RePPITS (RePPITS is the "Investigate & Act" engine). It holds a durable **goal**, maintains a **prioritized backlog**, works it down, learns each cycle, and loops until the goal is met / budget / escalation.

## Current task corpus (what we build on)
- **Claude Code Tasks** (`TaskCreate/Update/List/Get`) — the always-present, session-spanning execution corpus. Chosen as the **backlog source of truth**.
- **Linear** (optional, when MCP present) — mirror / PM layer.
- **`plans/*.md`** — local fallback (gitignored).
- Gap today: Tasks are a flat one-shot list — **no priority, score, goal, or continuous trigger**. This design adds those via task `metadata`.

## The outer loop ↔ mechanism mapping
| Loop node | Mechanism |
|---|---|
| **Trigger** | A driver supplies it: `/loop`, a scheduled cloud agent, an event Monitor, or "next backlog item." (Plugin defines behavior; driver supplies turns — see `reppit.md` "Running unattended".) |
| **Investigate & Act** | Pick the top-scored backlog item → run `/reppit <item>` (autonomous mode for substantial change; light fix for small). **Sensitive items keep full gates.** |
| **Backlog gen / Assign** | Write/refresh tasks in the Tasks corpus with scoring metadata (below). |
| **Review & learn** | Measure outcome vs goal → append a learning → **re-score the backlog** (the optimization) → check exit/escalation. |
| **↺ Loop** | Bounded (cycle/budget cap) + escalate + resumable (backlog lives in Tasks). |

## Backlog = Claude Code Tasks + metadata
Each backlog item is a Task; the optimization data lives in `metadata`:
```
metadata: {
  goalId:   "<goal slug>",           // which goal this serves
  value:    1-5,                      // expected impact toward the goal
  effort:   1-5,                      // estimated cost
  score:    value / effort,           // re-computed each Review&learn
  status_reason: "...",               // why blocked/deferred
  cycle:    <int>,                    // cycle it was created/last-touched
  learnings: "rolling 1-line digest"  // what the last attempt taught us
}
```
Goal object: a single "goal" Task (or a `plans/goal-loop/<goal>.md`) holding the **goal statement, success criteria (verifiable), budget/cycle cap, and a learnings log**. The loop reads only the goal + top-N scored open tasks each cycle — never the full history.

## Token economics over cycles (FIRST-CLASS — loops are token-hungry)
A naive loop's context grows every cycle (re-read code, growing backlog, accumulating learnings). Mitigations, in priority order:

1. **Per-cycle subagent isolation (Option A, always on).** Each *Investigate & Act* runs in an `Agent` subagent that reads the code/logs/tool output and returns **only** a compact verdict + new backlog items + a 1-line learning. The outer loop never holds the raw investigation — per-cycle context is bounded to the conclusion. This is the single biggest lever.
2. **Artifact-compacted backlog & learnings.** Backlog lives in Tasks; the learnings log lives on disk (goal file). Each cycle loads the **top-N scored items + a rolling learnings summary**, not the full history (CCR analog: full record on disk, retrieve on demand). Old learnings are **re-summarized (compressed) each cycle** so the digest stays capped.
3. **Headroom AST-aware compression (Option D / C, opt-in).** The loop *repeatedly reads source code* during Investigate & Act — the exact case where headroom's **`CodeCompressor` (AST-aware)** and `SmartCrusher` (JSON/logs) pay off, far more than in a one-shot run. When `REPPIT_HEADROOM=1`, the existing PostToolUse hook compresses those tool outputs before they enter context; for the Agent SDK driver, the headroom proxy/middleware (Option C) covers it. **This is the headroom payoff the goal-loop is built to exploit.** Default OFF; PHI-data-path review still applies.
4. **Per-cycle budget guard.** Track output tokens per cycle; if a cycle's cost spikes or the cumulative budget cap is hit, **escalate** (stop + summarize) rather than silently burning budget. Mirrors the bounded-loop cap (3) discipline.

> Net: Option A (subagent isolation + artifact compaction) keeps each cycle lean and portable; Option D's **AST compression** is what keeps the *code-reading* cost flat across many cycles — which is why "account for compression + AST" is a design requirement, not an add-on.

## Optimization / scoring
- Each cycle works the **highest `score` (value/effort)** open, unblocked task.
- *Review & learn* re-scores: items that proved harder than estimated get higher `effort`; newly-discovered high-impact gaps enter the backlog with high `value`. Over cycles the backlog converges toward the goal — measurable against the goal's success criteria.

## Bounds, exit, escalation, compliance
- **Exit** when the goal's success criteria are met, the cycle cap is reached, or the budget is exhausted.
- **Escalate** (stop + summarize) on: a stuck Investigate&Act bounded loop, a budget spike, or a sensitive change that fails Secure.
- **Resumable**: backlog + goal + learnings are durable (Tasks + goal file) → `/resume-reppit`-style reconstruction.
- **Compliance**: the loop never bypasses RePPITS gates for sensitive items; Secure always runs; nothing auto-pushes — the loop produces commits/PRs that still hit the final approval (or escalate).

## Driver story (reuse "Running unattended")
- Interactive Claude Code: the loop self-drives within an open session.
- Truly unattended (overnight/CI): `/loop`, a scheduled cloud agent, or an Agent SDK harness supplies triggers + turns. The plugin defines the behavior; the runner supplies the turns.

## Proposed build slices
1. **Backlog layer** — task `metadata` schema (value/effort/score/goalId/learnings) + a `backlog-scoring.md` convention; wire scoring into `make-plan` and re-scoring into `review-code`.
2. **`/reppit-goal` command** — the outer loop (goal intake → Trigger → Investigate&Act via `/reppit` → backlog gen/re-score → Review&learn → exit/escalate), with the token-economics rules above baked in.
3. **Compression hooks for the loop** — document/enable Option D AST compression specifically for the loop's Investigate&Act reads; per-cycle budget guard.
4. **Docs** — README "Goal-loop mode" section + diagram; CHANGELOG; version bump.

## Decisions
- **Default trigger = next item.** Each cycle auto-selects the highest-scored open, unblocked backlog task; no external tick required to advance within a session. (A driver is still needed for truly unattended runs — see "Driver story".)
- **Scoring = sophisticated, model-set (RICE).** The model estimates Reach × Impact × Confidence ÷ Effort per item and writes it to metadata; re-estimated each Review&learn. User can override any factor. (See `backlog-scoring.md`.)
- **Goal = free text + model judge.** The goal is free-text with free-text success criteria; the model judges "met / not met / partial" each cycle. (No runnable-check requirement — kept flexible per request.)
- **Option D AST compression = hard recommendation for goal-loops.** Still default-OFF and PHI-reviewed, but the docs and the command **actively recommend enabling `REPPIT_HEADROOM=1`** for loop runs, because the loop's repeated code reads are exactly headroom's `CodeCompressor` (AST) sweet spot. The command surfaces the recommendation at goal intake.

## Build status
Building as v0.4.0. Slices: (1) `backlog-scoring.md` (RICE convention) + optional scoring metadata in `make-plan`; (2) `commands/reppit-goal.md` (the outer loop); (3) token-economics + budget guard + Option-D hard-reco wired into the command; (4) README "Goal-loop mode" section + loop diagram, CHANGELOG, manifest version/keywords.
