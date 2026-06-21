Run a **dedicated goal-loop**: pursue a standing goal by repeatedly working down a prioritized backlog, learning each cycle, until the goal is met. This is the outer loop that wraps RePPITS (`/reppit` is its "act" step).

```
Trigger (next backlog item) → Investigate & Act → Backlog gen / Assign → Review & learn → ↺
```

## How to run it (so it actually loops)
- **Invoke:** `/loobster:reppit-loop <goal>` (plugin commands are namespaced; the bare `/reppit-loop` won't resolve unless you alias it as a project command).
- **One invocation runs cycles back-to-back in this session** — after each Review & learn, **immediately start the next cycle without asking**, and keep going until an exit condition (below). Do not stop after one item; running many cycles is the whole point.
- **For unattended / persistent looping** (close the laptop, overnight, CI): wrap it with a driver that re-invokes it — `/loop /loobster:reppit-loop <goal>`, a scheduled cloud agent, or an Agent SDK harness. The command resumes from the backlog each time. The plugin defines the behavior; the driver supplies the turns.

### Permissions (loop autonomy ≠ tool permissions)
The loop suppresses *its own* questions, but **Claude Code's tool-permission prompts are a separate layer** the loop can't control. The subagents this loop spawns do **not** inherit a session's runtime `--dangerously-skip-permissions` flag — they resolve their permission mode from settings. So if `permissions.defaultMode` is `auto` or `default`, you'll be prompted per file write **even though the main session shows bypass** (auto mode's classifier independently evaluates each subagent's tool calls). To run the loop prompt-free:
- Set `permissions.defaultMode: "bypassPermissions"` in `~/.claude/settings.json` (a launch flag alone is not enough for subagents).
- Add a `permissions.deny` list (e.g. recursive deletes, force-push, hard-reset, `.env` reads) — `deny`/`ask` rules still fire in bypass, so you keep guardrails.
- Then restart the session (settings load at start).

## This command is executable, not advisory — do these concrete steps
On invocation, **actually perform** the following (don't just describe them):

### Setup
1. Restate the goal in one line and write **free-text success criteria**. Create a goal record: `TaskCreate` a task titled `GOAL: <one-line goal>` with `metadata.kind="goal"`, `metadata.goalId="<slug>"`, the success criteria, and `metadata.maxCycles` (default 10). Also write `plans/loop/<slug>.md` with the goal + an empty learnings log.
2. **Recommend compression** (loops re-read code every cycle): tell the user "set `REPPIT_HEADROOM=1` to compress repeated code reads (README › Token reduction; PHI caveat applies)." Proceed regardless.
3. **Seed the backlog:** `TaskCreate` one task per known work item, each with `metadata.goalId=<slug>` and a RICE score per `${CLAUDE_PLUGIN_ROOT}/commands/backlog-scoring.md`. For large scoped items, run `/make-plan` to decompose — its sub-tasks join the backlog.

### The loop — repeat until an exit condition
1. **Trigger (next item):** first **consume relevant signals** from the shared hub (see `${CLAUDE_PLUGIN_ROOT}/commands/signals.md`) — read `signals/*.md` with `status: new|ack` and a `relevance` tag this goal cares about; a high-confidence signal may outrank the backlog (or spawn a new scored task). Then `TaskList`, filter to open, unblocked tasks for this `goalId`, pick the highest `metadata.score` (ties → lowest effort, then lowest id). If none remain → go to step 4 to decide done-vs-new-work.
2. **Investigate & Act — in a subagent** (`Agent`, so the heavy reads stay out of the loop's context): the subagent investigates the item, then **acts** — substantial change → run `/reppit <item>` (autonomous mode; sensitive items still hit full gates + Secure); small fix → do it directly. It returns **only** a compact result: outcome, any new backlog items (with RICE), and a one-line learning. `TaskUpdate` the worked item (`in_progress`→`completed`, or keep `in_progress` + record the blocker).
   - **Do not force `isolation: "worktree"` on the act subagent.** A worktree writes into an untrusted `.claude/worktrees/<id>/` path, and combined with non-bypass permission modes it surfaces a write-prompt per file (see "Permissions" above) — which defeats unattended running. Use worktree isolation only when genuinely parallelizing independent sub-issues **and** the session is in `bypassPermissions`; otherwise run the act in the loop's own permission context.
3. **Backlog gen / Assign:** `TaskCreate` the new items the subagent surfaced (scored, tagged with `goalId`).
4. **Review & learn:** judge the cycle's result against the goal's success criteria → **met / partial / not-met**. **Use a separate verifier subagent — never let the agent that did step 2 (Act) judge its own work** (see the "Never self-verify" rule in `reppit.md`); the judge gets the diff + criteria and returns its verdict. Then: append a one-line learning to `plans/loop/<slug>.md` (re-summarize the log so it stays small); **re-score** the backlog from what this cycle taught (never overwrite user-set factors). **Emit signals**: if this cycle surfaced something other loops/teammates should know (a friction, an opportunity, a fact), write it to the shared hub per `${CLAUDE_PLUGIN_ROOT}/commands/signals.md` (stamp `author`, dedup first, **no PHI**). Mark any signal you acted on this cycle `acted`/`archived`.
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
