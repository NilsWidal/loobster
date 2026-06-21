Run a **dedicated goal-loop**: pursue a standing goal by repeatedly working down a prioritized backlog, learning each cycle, until the goal is met. This is the outer loop that wraps RePPITS (`/reppit` is its "act" step).

```
Trigger (next backlog item) → Investigate & Act → Backlog gen / Assign → Review & learn → ↺
```

## How to run it (so it actually loops)
- **Invoke:** `/reppit-health:reppit-loop <goal>` (plugin commands are namespaced; the bare `/reppit-loop` won't resolve unless you alias it as a project command).
- **One invocation runs cycles back-to-back in this session** — after each Review & learn, **immediately start the next cycle without asking**, and keep going until an exit condition (below). Do not stop after one item; running many cycles is the whole point.
- **For unattended / persistent looping** (close the laptop, overnight, CI): wrap it with a driver that re-invokes it — `/loop /reppit-health:reppit-loop <goal>`, a scheduled cloud agent, or an Agent SDK harness. The command resumes from the backlog each time. The plugin defines the behavior; the driver supplies the turns.

## This command is executable, not advisory — do these concrete steps
On invocation, **actually perform** the following (don't just describe them):

### Setup
1. Restate the goal in one line and write **free-text success criteria**. Create a goal record: `TaskCreate` a task titled `GOAL: <one-line goal>` with `metadata.kind="goal"`, `metadata.goalId="<slug>"`, the success criteria, and `metadata.maxCycles` (default 10). Also write `plans/loop/<slug>.md` with the goal + an empty learnings log.
2. **Recommend compression** (loops re-read code every cycle): tell the user "set `REPPIT_HEADROOM=1` to compress repeated code reads (README › Token reduction; PHI caveat applies)." Proceed regardless.
3. **Seed the backlog:** `TaskCreate` one task per known work item, each with `metadata.goalId=<slug>` and a RICE score per `${CLAUDE_PLUGIN_ROOT}/commands/backlog-scoring.md`. For large scoped items, run `/make-plan` to decompose — its sub-tasks join the backlog.

### The loop — repeat until an exit condition
1. **Trigger (next item):** `TaskList`, filter to open, unblocked tasks for this `goalId`, pick the highest `metadata.score` (ties → lowest effort, then lowest id). If none remain → go to step 4 to decide done-vs-new-work.
2. **Investigate & Act — in a subagent** (`Agent`, so the heavy reads stay out of the loop's context): the subagent investigates the item, then **acts** — substantial change → run `/reppit <item>` (autonomous mode; sensitive items still hit full gates + Secure); small fix → do it directly. It returns **only** a compact result: outcome, any new backlog items (with RICE), and a one-line learning. `TaskUpdate` the worked item (`in_progress`→`completed`, or keep `in_progress` + record the blocker).
3. **Backlog gen / Assign:** `TaskCreate` the new items the subagent surfaced (scored, tagged with `goalId`).
4. **Review & learn:** model-judge the cycle's result against the goal's success criteria → **met / partial / not-met**; append a one-line learning to `plans/loop/<slug>.md` (re-summarize the log so it stays small); **re-score** the backlog from what this cycle taught (never overwrite user-set factors).
5. **Loop:** if no exit condition, **go straight back to step 1** — do not pause for the user between cycles.

### Exit & escalation
- **Exit** when: the model judges the goal **met**, the backlog is empty with no new work justified, `maxCycles` is reached, or `--budget` is exhausted. On exit, summarize: goal status, what shipped (commits/PRs), remaining backlog, key learnings.
- **Escalate** (stop + summarize, hand back) on: a stuck Investigate&Act loop (its cap), a sensitive change that fails Secure, or a per-cycle token spike. Never auto-push past unresolved work.

## Arguments
- **goal**: free-text goal + success criteria. Required.
- **--max-cycles N**: hard cap (default 10).
- **--budget T**: optional output-token budget; escalate when exhausted.

## Token economics (loops are token-hungry — enforce)
- **Per-cycle subagent isolation** (loop step 2) is mandatory — the loop holds conclusions, not raw reads.
- **Artifact compaction:** each cycle loads the goal + top-N scored tasks + the rolling learnings digest, never the full history; re-compress old learnings each cycle.
- **Option D AST compression is the hard recommendation for loops** (`REPPIT_HEADROOM=1`) — repeated code reads are headroom's `CodeCompressor` (AST) sweet spot. Agent SDK driver → headroom proxy/middleware.
- **Budget guard:** track output tokens per cycle; on a spike or `--budget` exhaustion, escalate rather than silently continue.

## Resuming & compliance
- Resumable: goal + backlog + learnings are durable (Tasks + `plans/loop/<slug>.md`); `TaskList` for the `goalId` reconstructs progress — continue from the highest-scored open item (see `/resume-reppit`).
- Never bypasses RePPITS gates for sensitive items, never skips Secure, never auto-pushes — it produces commits/PRs that still hit the final approval, or it escalates.
