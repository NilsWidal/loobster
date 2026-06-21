Run a dedicated goal-loop: pursue a standing goal by repeatedly working down a prioritized backlog, learning each cycle, until the goal is met.

This is the **outer loop** that wraps RePPITS. RePPITS (`/reppit`) builds one thing; this drives many cycles toward a goal:

```
Trigger → Investigate & Act → Backlog gen / Assign → Review & learn → ↺
```

## Arguments
- **goal**: A free-text goal with success criteria (e.g. "Get the auth module to HIPAA-clean: no PHI in logs, all access audited"). Required.
- **--max-cycles N**: Hard cycle cap (default 10). The loop stops and summarizes when reached.
- **--budget T**: Optional output-token budget; escalate when exhausted.
- **--driver**: How the loop is triggered for unattended runs (`loop` | `cron` | `sdk`); default is in-session "next item" (see Triggering).

## Setup — goal intake
1. Restate the goal in one line and define **free-text success criteria** (what "done" looks like). Save a goal record: a goal Task (or `plans/goal-loop/<slug>.md`) holding the goal, success criteria, caps, and an empty learnings log. Assign a `goalId` slug.
2. **Recommend Option D compression.** Because a goal-loop re-reads code every cycle, strongly recommend the user enable headroom AST compression for this run: "Goal-loops are token-heavy — set `REPPIT_HEADROOM=1` (see README › Token reduction) to compress repeated code reads. Off by default; review the PHI-data-path caveat first." Proceed either way.
3. **Seed the backlog.** Generate the initial backlog as Claude Code Tasks (`TaskCreate`), each scored per `${CLAUDE_PLUGIN_ROOT}/commands/backlog-scoring.md` (RICE in `metadata`, tagged with `goalId`). For substantial scoped work, you may run `/make-plan` to decompose — its sub-tasks join the backlog.

## The loop (one cycle)
Repeat until an exit condition (below):

1. **Trigger — next item.** Select the highest-`score` open, unblocked Task for this `goalId` (`TaskList` → filter → pick top; ties → lowest effort, then lowest id). If the backlog is empty, go to Review & learn to decide whether the goal is met or new work is needed.
2. **Investigate & Act — in an isolated subagent.** Delegate the work to an `Agent` so the heavy reading stays out of the loop's context (token discipline — see `${CLAUDE_PLUGIN_ROOT}/commands/token-discipline.md`). The subagent:
   - investigates the item against the goal,
   - **acts**: for a substantial change, runs `/reppit <item>` (autonomous mode — sensitive items still hit full gates and Secure); for a small fix, does it directly,
   - returns **only** a compact result: outcome, any new backlog items (with RICE estimates), and a one-line learning. Never return raw file contents to the loop.
   `TaskUpdate` the worked item (`in_progress`→`completed`, or keep `in_progress` + record blocker).
3. **Backlog gen / Assign.** `TaskCreate` the new items the subagent surfaced, scored per `backlog-scoring.md`, tagged with `goalId`.
4. **Review & learn.** Model-judge the cycle's outcome against the goal's success criteria → **met / partial / not-met**. Append a one-line learning to the goal log (re-summarize/compress the log so it stays capped). **Re-score** the backlog from what this cycle taught (never overwrite user-set factors).

## Exit & escalation
- **Exit** when: the model judges the goal **met**, the backlog is empty with no new work justified, `--max-cycles` is reached, or `--budget` is exhausted. On exit, summarize: goal status, what shipped, the remaining backlog, and key learnings.
- **Escalate** (stop + summarize, hand back to the user) on: an Investigate&Act bounded loop that hit its cap, a sensitive change that fails Secure, or a per-cycle token spike. Never auto-push past unresolved work.

## Token economics (loops are token-hungry — enforce this)
- **Per-cycle subagent isolation** (step 2) is mandatory: the loop holds only conclusions, not the cycle's raw reads.
- **Artifact compaction**: each cycle loads the goal + top-N scored tasks + the rolling learnings digest — never the full history. Old learnings are re-compressed each cycle.
- **Option D AST compression is the hard recommendation for loops** (`REPPIT_HEADROOM=1`): the repeated code reads are headroom's `CodeCompressor` (AST) sweet spot. For an Agent SDK driver, use the headroom proxy/middleware instead.
- **Budget guard**: track output tokens per cycle; on a spike or `--budget` exhaustion, escalate rather than silently continue.

## Triggering & unattended runs
- **Default (in-session, "next item"):** the loop advances itself cycle to cycle while the session is open and the agent keeps taking turns.
- **Unattended:** supply a driver — `/loop`, a scheduled cloud agent, or an Agent SDK harness re-invokes `/reppit-goal` (it resumes from the backlog). The plugin defines the behavior; the driver supplies the turns. See `${CLAUDE_PLUGIN_ROOT}/commands/reppit.md` › "Running unattended".

## Resuming
The goal, backlog, and learnings are durable (Tasks + goal file), so an interrupted goal-loop resumes: `TaskList` for this `goalId` reconstructs the backlog and progress; continue from the highest-scored open item (see `/resume-reppit`).

## Compliance
The loop never bypasses RePPITS gates for sensitive items, never skips Secure, and never auto-pushes. It produces commits/PRs that still reach the final approval — or it escalates.
