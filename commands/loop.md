Run a **dedicated goal-loop**: pursue a standing goal by repeatedly working down a prioritized backlog, learning each cycle, until the goal is met. This is the outer loop that wraps RePPITS (`/run` is its "act" step).

```
Trigger (next backlog item) → Investigate & Act → Backlog gen / Assign → Review & learn → ↺
```

## How to run it (so it actually loops)
- **Invoke:** `/loobster:loop <goal>` (plugin commands are namespaced; the bare `/loop` won't resolve unless you alias it as a project command).
- **One invocation runs cycles back-to-back in this session** — after each Review & learn, **immediately start the next cycle without asking**, and keep going until an exit condition (below). Do not stop after one item; running many cycles is the whole point.
- **Self-driving — no wrapper needed.** `/loobster:loop <goal>` arms its **own** durable re-entry; you do **not** prefix it with the `/loop` scheduler. At setup (and re-armed at the end of each turn while `status: active`) it schedules a re-invocation of *itself* so a turn boundary or a **dead turn** (API drop, crash) auto-resumes the loop from its checkpoint:
  - **In-session durability:** `ScheduleWakeup(prompt: "/loobster:loop <goal>", delaySeconds: ~90)` — a heartbeat that re-enters the loop each tick and after any dead turn. Re-arm while `status: active`; **stop arming on exit**.
  - **Closed-session / overnight durability:** *also* `CronCreate` (or `/schedule`) the same `/loobster:loop <goal>` so it survives the session being closed. `CronDelete` it on exit.
  - If neither tool is available in your runtime, the loop still runs cycles in-session and the Stop hook covers graceful stops; for hard-crash durability there, supply an external driver (cron / Agent SDK).
- **Crash resilience, in one line:** the self-armed re-entry re-fires `/loobster:loop <goal>` after a dead turn → it self-heals (reclaims stale `in_progress`, continues from the checkpoint — see *Self-healing* below). The bundled **Stop hook** (`hooks/hooks.json` → `bin/loop-rearm.py`) additionally refuses a premature *graceful* stop while `status: active`. Together a dead turn, a crash, or a milestone-pause all resume automatically. Disable the hook with `LOOBSTER_LOOP_REARM=0`.

### Permissions (loop autonomy ≠ tool permissions)
The loop suppresses *its own* questions, but **Claude Code's tool-permission prompts are a separate layer** the loop can't control. The subagents this loop spawns do **not** inherit a session's runtime `--dangerously-skip-permissions` flag — they resolve their permission mode from settings. So if `permissions.defaultMode` is `auto` or `default`, you'll be prompted per file write **even though the main session shows bypass** (auto mode's classifier independently evaluates each subagent's tool calls). To run the loop prompt-free:
- Set `permissions.defaultMode: "bypassPermissions"` in `~/.claude/settings.json` (a launch flag alone is not enough for subagents).
- Add a `permissions.deny` list (e.g. recursive deletes, force-push, hard-reset, `.env` reads) — `deny`/`ask` rules still fire in bypass, so you keep guardrails.
- Then restart the session (settings load at start).

## This command is executable, not advisory — do these concrete steps
On invocation, **actually perform** the following (don't just describe them):

### Setup
1. Restate the goal in one line and write **free-text success criteria**. Create a goal record: `TaskCreate` a task titled `GOAL: <one-line goal>` with `metadata.kind="goal"`, `metadata.goalId="<slug>"`, the success criteria, and `metadata.maxCycles` (default 10). Also write `plans/loop/<slug>.md` with **frontmatter** (`status: active`, `goalId: <slug>`, the one-line `goal`, `cycle: 0`) followed by the success criteria + an empty learnings log. The `status: active` marker is **load-bearing**: the Stop hook (`bin/loop-rearm.py`) reads it to keep the loop running across turn boundaries — set it to `done` **only** on a real exit/escalation.
2. **Recommend compression** (loops re-read code every cycle): tell the user "set `LOOBSTER_HEADROOM=1` to compress repeated code reads (README › Token reduction; PHI caveat applies)." Proceed regardless.
3. **Seed the backlog:** `TaskCreate` one task per known work item, each with `metadata.goalId=<slug>` and a RICE score per `${CLAUDE_PLUGIN_ROOT}/commands/backlog-scoring.md`. For large scoped items, run `/make-plan` to decompose — its sub-tasks join the backlog.
4. **Arm self-re-entry (this is what makes the single command self-driving).** Schedule the loop's own durable driver so you never wrap it: call `ScheduleWakeup(prompt: "/loobster:loop <goal>", delaySeconds: 90)` now, and for closed-session durability also `CronCreate` the same prompt. Record the wakeup/cron id in the marker frontmatter (`reentry: <id>`) so Exit can cancel it. (If these tools aren't available, skip — the loop still runs in-session + the Stop hook covers graceful stops.)

### Self-healing — do this on every (re)entry (crash-safe resume)
A previous run may have died mid-cycle (API drop, crash, stop). Before picking work, reconcile durable state:
1. **Check the marker status first.** If `plans/loop/<slug>.md` `status` is **not** `active` — it's `paused` (a human approval gate is pending) or `done` (finished/escalated) — the loop is **intentionally halted**: do **not** resume or re-arm the driver; report the state and stop. A self-re-entry wakeup that fires on a `paused`/`done` loop must be a no-op (this is what keeps an approval gate from being auto-driven past). Only continue when `status: active`.
2. **Reload** the goal task (`metadata.kind=goal`) + `plans/loop/<slug>.md` (cycle, learnings). If the goal task is gone but the marker exists, rebuild from `TaskList` for the `goalId`.
3. **Reclaim stale in-progress.** Any task `in_progress` whose `metadata.heartbeatAt` is missing or older than ~2 cycles was **interrupted, not running** → it becomes the next item. **Check what already landed first** (git status/diff, committed sub-issues, sub-task states) and **continue** it — never redo completed work, never double-commit. (This is the M19-style "stranded in_progress after a connection drop" case.)
4. Then enter the loop. (`/resume` routes a goal-loop straight here.)

### The loop — repeat until an exit condition
1. **Trigger (next item):** first **consume relevant signals** from the shared hub (see `${CLAUDE_PLUGIN_ROOT}/commands/signals.md`) — read `signals/*.md` with `status: new|ack` and a `relevance` tag this goal cares about; a high-confidence signal may outrank the backlog (or spawn a new scored task). Then `TaskList`, filter to open, unblocked tasks for this `goalId`, pick the highest `metadata.score` (ties → lowest effort, then lowest id). If none remain → go to step 4 to decide done-vs-new-work.
2. **Investigate & Act — in a subagent** (`Agent`, so the heavy reads stay out of the loop's context): the subagent investigates the item, then **acts** — substantial change → run `/run <item>` (autonomous mode; sensitive items still hit full gates + Secure); small fix → do it directly. It returns **only** a compact result: outcome, any new backlog items (with RICE), and a one-line learning. `TaskUpdate` the worked item (`in_progress`→`completed`, or keep `in_progress` + record the blocker). **Heartbeat:** when you set a task `in_progress`, stamp `metadata.startedAt` + `metadata.leaseId` and refresh `metadata.heartbeatAt` as it progresses — that timestamp is what lets a later entry distinguish an *interrupted* task from a *running* one (step Self-healing).
   - **Do not force `isolation: "worktree"` on the act subagent.** A worktree writes into an untrusted `.claude/worktrees/<id>/` path, and combined with non-bypass permission modes it surfaces a write-prompt per file (see "Permissions" above) — which defeats unattended running. Use worktree isolation only when genuinely parallelizing independent sub-issues **and** the session is in `bypassPermissions`; otherwise run the act in the loop's own permission context.
3. **Backlog gen / Assign:** `TaskCreate` the new items the subagent surfaced (scored, tagged with `goalId`).
4. **Review & learn:** judge the cycle's result against the goal's success criteria → **met / partial / not-met**. **Use a separate verifier subagent — never let the agent that did step 2 (Act) judge its own work** (see the "Never self-verify" rule in `run.md`); the judge gets the diff + criteria and returns its verdict. Then: append a one-line learning to `plans/loop/<slug>.md` (re-summarize the log so it stays small); **re-score** the backlog from what this cycle taught (never overwrite user-set factors). **Emit signals**: if this cycle surfaced something other loops/teammates should know (a friction, an opportunity, a fact), write it to the shared hub per `${CLAUDE_PLUGIN_ROOT}/commands/signals.md` (stamp `author`, dedup first, **no PHI**). Mark any signal you acted on this cycle `acted`/`archived`.
5. **Loop:** if no exit condition, **go straight back to step 1** — do not pause for the user between cycles.

### Exit & escalation — the ONLY reasons to stop
- **Exit** only when one of these holds: (a) the model judges the goal **met**, (b) the backlog is empty with no new work justified, (c) `maxCycles` reached, or (d) `--budget` exhausted. On exit, **set `status: done` in `plans/loop/<slug>.md`** (releases the Stop-hook re-arm) **and cancel the self-re-entry** — stop arming `ScheduleWakeup` and `CronDelete` the cron recorded in the marker's `reentry` id — then summarize: goal status, what shipped (commits/PRs), remaining backlog, key learnings.
- **Escalate** (stop + summarize + set `status: done` + cancel the self-re-entry, hand back) only on: a stuck Investigate&Act loop (its cap), a sensitive change that fails Secure, or a per-cycle token spike. Never auto-push past unresolved work.
- **NOT exit conditions — do not stop or pause to ask; continue straight to the next cycle:** reaching a "clean milestone", finishing a cluster / PR / batch, having "done a lot", or hesitating to "auto-spend" more cycles/tokens. **A milestone is not the goal.** If you catch yourself about to write *"say keep going"*, *"want me to continue?"*, or *"I'll hold here"* — **don't; keep going** until a real exit/escalation condition above. Spend is bounded by `maxCycles` and `--budget`, never by a voluntary hold. (The Stop hook enforces this for interactive runs.)
- **Human approval gates stay sacred.** The "never stop at a milestone" rule does **not** override the gates: if the act step reaches the **final commit/push approval**, a **sensitive Secure FAIL**, or any mandatory gate, set the marker `status: paused` (or `done`) **before** stopping so the Stop hook allows it — the loop **never** pushes past an approval or unresolved FAIL to stay alive. Resume after the human responds.
- **Checkpoint each cycle:** update `cycle` (+ a one-line current position) in the marker before/after the act step, so a crash mid-cycle resumes precisely.

## Arguments
- **goal**: free-text goal + success criteria. Required.
- **--max-cycles N**: hard cap (default 10).
- **--budget T**: optional output-token budget; escalate when exhausted.

## Token economics (loops are token-hungry — enforce)
- **Per-cycle subagent isolation** (loop step 2) is mandatory — the loop holds conclusions, not raw reads.
- **Artifact compaction:** each cycle loads the goal + top-N scored tasks + the rolling learnings digest, never the full history; re-compress old learnings each cycle.
- **Option D AST compression is the hard recommendation for loops** (`LOOBSTER_HEADROOM=1`) — repeated code reads are headroom's `CodeCompressor` (AST) sweet spot. Agent SDK driver → headroom proxy/middleware.
- **Budget guard:** track output tokens per cycle; on a spike or `--budget` exhaustion, escalate rather than silently continue.

## Resuming & compliance
- Resumable: goal + backlog + learnings are durable (Tasks + `plans/loop/<slug>.md`); `TaskList` for the `goalId` reconstructs progress — continue from the highest-scored open item (see `/resume`).
- Never bypasses RePPITS gates for sensitive items, never skips Secure, never auto-pushes — it produces commits/PRs that still hit the final approval, or it escalates.
