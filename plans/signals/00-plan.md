# Plan: Signals Hub (hybrid) + dynamic dashboard + optional GitHub Pages

**Tier:** sensitive (shared, committed data sink; could capture PHI-derived content). Full gates; Secure mandatory.
**Use case:** **multi-person teams working on one codebase** — each person's loops/agents emit signals to a shared, team-visible hub so the whole team sees what's going on. This is a team coordination layer, not a single-user store.
**Chosen:** Proposal 3 (hybrid) — `signals/*.md` files are the **source of truth** (file-per-signal = merge-conflict-safe for multi-writer), with an optional `kind:"signal"` Claude Code Task mirror for querying. Plus a dynamic team dashboard and an opt-in GitHub Pages publish path.
**Research:** `research/signals-system.md` · **Proposals:** `research/proposals-signals.md` + `research/signals/*.html`.

## Goal / done
- Any person's loop/agent (or a human) can **emit** a signal to one shared hub and **consume** relevant ones (emit-first, domain-agnostic) — and **the whole team sees it**.
- Signals carry **`author`** attribution so the team knows who flagged what.
- A **dynamic team-status dashboard** visualizes current state (by status / author / source-loop / type / timeline) and reflects updates on refresh — works from `file://` and when served.
- **Optional** GitHub Pages publishing gives the team one shared status URL, updated on each push — gated (private repo / non-PHI).
- PHI never lands in signals (patterns/summaries only) — this is the **critical enabler** that lets the hub be committed + shared; a Secure check enforces it.

## Architecture (data flow)
```
loop emit ─► signals/<id>.md (frontmatter+body)  ◄─ source of truth
                  │  bin/signals-build.py (parse)
                  ▼
        signals/data.js  (window.SIGNALS=[...] — file:// safe)
        signals/data.json (fetch/poll — served/Pages)
        signals/INDEX.md  (human/auditable mirror)
                  ▼
        signals/dashboard.html  (loads data.js; renders; manual+auto refresh)
                  ▼ (optional, non-PHI)
        GitHub Pages  ◄─ .github/workflows/signals-pages.yml on push
loop consume ◄─ read signals/*.md by tag/status  (+ optional kind:signal Task query)
```

## Storage / compliance decision
- Default `signals/` is **tracked / committed (shared)** — the team-coordination use case requires everyone to see signals, so they sync via git push/pull. (Reverses the single-user local default.)
- Because signals are committed + shared, the **PHI-exclusion rule is the load-bearing control**: signals must be non-PHI patterns/summaries, enforced by the Secure check. This is what makes a *shared* hub safe on a healthcare codebase.
- **GitHub Pages** = an extension of the already-shared data → opt-in, and on a **private repo with private Pages** (or non-PHI repos). A public-repo Pages site would expose business/PHI signals — never for healthcare. Documented as a gated data-path control.
- Multi-writer: file-per-signal + unique ids (`<ts>-<author>-<slug>`) keep merge conflicts rare; same-key signals from different authors are deduped (tally, not duplicate).

## Sub-issues (ordered, one commit each)
1. **`commands/signals.md` — the hub.** Signal schema (id/**author**/source/ts/type/confidence/relevance/status/title/body); unique id `<ts>-<author>-<slug>` for multi-writer safety; emit (write `signals/<id>.md`), consume (read by tag/status), cross-author dedup (tally same-key), lifecycle (new→ack→acted→archived); **PHI-exclusion rule (load-bearing — signals are shared)**; optional `kind:signal` Task mirror. *(blocks 2,3)*
2. **Loop integration.** Emit hook in `reppit-loop.md` Review&learn (stamp `author`); consume hook in Trigger/Investigate; signal→RICE backlog task via `backlog-scoring.md`. *(needs 1)*
3. **`bin/signals-build.py` — data generator.** Parse `signals/*.md` → `signals/data.js` + `signals/data.json` + `signals/INDEX.md`. Robust (skip malformed), no PHI persisted by the tool. **Tests** in `tests/`. *(needs 1)*
4. **`templates/signals-dashboard.html` — dynamic team-status dashboard.** Loads `data.js` (global, file:// safe); renders counts, by-status, **by-author**, by-source-loop, by-type, recent timeline; manual Refresh + optional auto-reload; when served, also polls `data.json`. Validated by rendering. *(needs 3)*
5. **Optional GitHub Pages.** `.github/workflows/signals-pages.yml` template + docs to publish the dashboard; **gated non-PHI**; compliance note that Pages = tracked + public. *(needs 4)*
6. **Compliance + docs + release.** `compliance/org-controls-audit.md` signals + Pages data-path control; `secure.md` PHI-in-signals check; README "Signals" section + dashboard screenshot/diagram; CHANGELOG; `plugin.json`/`marketplace.json` version (0.5.0) + keywords. *(needs all)*

Deps: 1 → 2,3; 3 → 4; 4 → 5; 6 → all.

## Testing plan
- `bin/signals-build.py`: fixtures (3 signals incl. one malformed) → valid data.js/json/INDEX; malformed skipped; **PHI-shaped content flagged**.
- Dashboard: render with a sample `data.js`, confirm it shows counts/sections (validate via headless render).
- Secure: a PHI-shaped signal → FAIL in the signals check.
- Loop emit/consume + signal→task: dry-run fixtures.

## Open questions (Gate 3)
- [ ] Dashboard depth now: status board only, or also charts (by-type bar, timeline)?
- [ ] Pages: ship the workflow template now, or docs-only (defer the Action)?
- [ ] Auto-refresh cadence default for the local dashboard.
