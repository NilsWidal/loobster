Resume a paused, interrupted, or crashed RePPITS workflow by reconstructing state from Claude Code Tasks.

The full `/run` flow keeps its state in the conversation context, which is lost on a crash, a `stop`/`pause`, or a new session. The durable record is the Claude Code Tasks created during Phase 3 (Plan) and advanced during Implement/Test/Secure. This command rebuilds from that record and continues from the last incomplete step.

## Arguments
- **topic** (optional): The original topic or Linear issue ID. If omitted, infer from the open Tasks and the local `plans/` directory.

## Steps
1. **Read the durable state:**
   - Run `TaskList` to get all tasks, their status, owners, and `blockedBy` edges.
   - For the parent/plan context, read the local plan (e.g. `plans/<feature>/00-parent-design-doc.md`) and any matching Linear parent issue if Linear MCP is available.
2. **Reconstruct progress:**
   - `completed` tasks = work already done — do **not** redo them. Trust the Task record over conversation memory.
   - `in_progress` tasks = work that was interrupted mid-flight. Re-read the corresponding files/diff to see how far it got before continuing. (A goal-loop stamps `metadata.heartbeatAt`; an `in_progress` task with a stale or absent heartbeat was **interrupted, not running** — reclaim and continue it, never redo.)
   - `pending` tasks with an empty `blockedBy` = the next available work, lowest ID first.
   - `pending` tasks still `blockedBy` open tasks = not yet startable.
3. **Confirm the reconstructed state with the user** before resuming: list what's done, what was in-flight, and what's next. Play the gate sound (`afplay /System/Library/Sounds/Glass.aiff &`) and ask: "Resume from here?"
4. **Continue the workflow** from the first available task, following `${CLAUDE_PLUGIN_ROOT}/commands/run.md` from the matching phase. Re-apply the Phase 0 tier and gate policy that was recorded in the plan.

## Notes
- **Goal-loop resume:** if a `metadata.kind=goal` task or a `plans/loop/<slug>.md` with `status: active` exists, this is a **goal-loop**, not a one-shot `/run`. Resume by following `${CLAUDE_PLUGIN_ROOT}/commands/loop.md` → *Self-healing — do this on every (re)entry* (reclaim stale `in_progress`, idempotent-continue), then run cycles continuously to a real exit condition. Confirm once at resume, then **do not pause between cycles** — that's the loop's contract, and the Stop hook (`bin/loop-rearm.py`) keeps it alive across turns.
- This command never re-implements completed work; the Task record is the source of truth.
- If `TaskList` is empty and no `plans/` artifact exists, there is nothing to resume — say so and suggest starting a fresh `/run`.
- Pairs with the Phase 6 convergence loop, which externalizes each iteration's outcome so a mid-loop crash is resumable.
