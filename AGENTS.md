# Loobster — agent instructions (AGENTS.md)

Loobster is a **loop harness**: it runs AI-assisted development as a gated, verifiable, autonomous loop instead of one-shot prompts. This file is the cross-tool entry point (Codex, and any agent that reads `AGENTS.md`). The full, invocable steps live as **skills** in [`.agents/skills/`](.agents/skills/) (generated from [`commands/`](commands/), the canonical source).

It implements the **RePPITS** method — Research → Propose → Plan → Implement → Test → Secure (the RePPIT framework by Mihail Eric, plus a Secure phase).

## How to run it

- **Codex / `.agents/skills` agents:** invoke a skill explicitly (`/skills` or `$run`) or let it trigger implicitly. The skills are `run`, `loop`, `signals`, `verify-frontend`, `research-codebase`, `make-proposals`, `make-plan`, `implement`, `review-code`, `secure`, `resume` (plus `token-discipline` and `backlog-scoring`, which are **reference docs in `reference/`** read by the skills above — not invoked directly).
- **Claude Code:** the same files run as plugin commands (`/loobster:run`, etc.).
- Start with **`run`** for a feature/change end-to-end; **`loop`** for a continuous goal-loop; **`signals`** to coordinate across loops/people.
- **The `loop` skill self-drives** via a single-runner lease (an **atomic lock file**, `bin/loop-lease.py` — one instance per worktree) and **never re-enters a `paused`/`done` loop** (that's what keeps an approval gate from being auto-driven past). In runtimes without `CronCreate`/`ScheduleWakeup` (e.g. Codex) it runs in-session; supply an external driver for closed-session durability.

## Non-negotiable rules (apply to every skill)

1. **Never self-verify.** Every Test / Secure / review / frontend-verify step runs in a **separate verifier agent** (or CI) that did **not** produce the work. The implementer never grades its own diff.
2. **Right-size first.** Classify each task **trivial / standard / sensitive**. Sensitive = touches PHI, auth, crypto, audit logging, data retention/deletion, multi-tenant isolation, or infra. When in doubt, choose sensitive.
3. **Gates by tier.** Standard/sensitive changes stop at approval gates between phases; **sensitive never auto-advances**. Trivial may collapse early gates only with `--auto`. Flags: `--auto` (trivial-only early auto-advance, ignored for sensitive), `--manual` (force every gate), `--autonomous` (pre-select Gate-3 autonomous mode).
4. **Secure always runs.** The Secure phase runs for every tier and **blocks on any FAIL** — never skipped, never bypassed.
5. **Bounded autonomy.** When Secure finds FAILs, the Implement→Test→Secure fix loop self-drives up to a **cap of 3 iterations**, then **escalates to a human**. It never silently commits past unresolved FAILs.
6. **The final commit/push always stops for human approval** — in every mode. Nothing auto-pushes.
7. **Autonomous mode** (Gate 3 / `--autonomous`) auto-advances only the intermediate Implement/Test review prompts; **Test and Secure still run and block on findings**, and the final commit/push always stops.

## Signals (cross-loop coordination)

Any loop/agent/teammate **emits** observations (friction / opportunity / fact) as one markdown file per signal under `signals/`, and any loop **consumes** the relevant ones. File-per-signal is merge-safe for multiple writers; `author` gives attribution. **No PHI in a signal** — they are committed and shared. See the `signals` skill.

## Compliance (configurable)

Per-repo, enable any of **HIPAA / HITRUST / ISO 27001 / SOC 2** via `.claude/loobster-frameworks.json` (`{ "frameworks": ["soc2","iso27001"] }`); defaults to all four. The `secure` skill runs only the enabled checklists against the diff and separates code-verifiable findings from organizational controls. Healthcare is one profile, not a requirement.

## Token discipline

Subagent context-isolation + artifact compaction are always on (see the `token-discipline` skill). For automatic wire-level compression with [headroom](https://github.com/headroomlabs-ai/headroom) (`pip install "headroom-ai[code]"`):
- **In Codex / Agent SDK:** use headroom's **proxy / middleware** (Option C) — run `headroom proxy` and point the model base URL at it. (Codex has no PostToolUse hook, so the Claude-Code hook below does not apply here.)
- **In Claude Code:** the bundled `PostToolUse` hook (Option D) is on by default; `LOOBSTER_HEADROOM=0` disables it. On PHI repos, set `LOOBSTER_HEADROOM=0` until headroom has had a data-path review.

## Regenerating the skills

`.agents/skills/**` is generated — edit `commands/*.md` and run `python3 bin/build-codex-skills.py` (or `--check` in CI to detect drift).

---
Apache-2.0 · github.com/NilsWidal/loobster · docs: nilswidal.github.io/loobster
