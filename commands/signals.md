The shared **signals hub**: a central place where any loop, agent, or person on a codebase emits signals (observations / frictions / opportunities) and any loop consumes the relevant ones. Built for **multi-person teams on one codebase** — signals are committed and synced so the whole team sees what's going on.

```
emit ─► signals/<id>.md ◄─ source of truth ─► consume (by tag/status)
```

## What a signal is
A small, structured observation — never a task, never raw data. One signal = one file under `signals/`.

## Signal file format
`signals/<id>.md`, where **`<id>` = `<YYYY-MM-DD>-<author>-<slug>`** (date + author + short slug) so concurrent writers never collide and files are self-describing.

```markdown
---
id: 2026-06-21-nils-export-too-hidden
author: nils                  # who/which agent emitted it (team attribution)
source: support-loop          # the loop/context it came from (or "manual")
ts: 2026-06-21T14:30:00Z
type: friction                # friction | opportunity | fact
confidence: 0.8               # 0.5 (hunch) | 0.8 (likely) | 1.0 (confirmed)
relevance: [product, onboarding]   # tags that consuming loops filter on
status: new                   # new | ack | acted | archived
title: Export is too hidden
---
5 users this week asked how to export. The action is 3 clicks deep. (count: 5)
```

> **PHI exclusion — load-bearing.** Because signals are committed and shared across the team, they must be **non-PHI patterns/summaries only** — "5 users asked about export," never "patient Jane asked…". No names, DOB, SSN, MRN, emails, phone numbers, or free-text that could identify a person. The Secure phase checks this; a PHI-shaped signal is a FAIL.

## Emit (the primary action — keep it trivial)
Any loop, agent, or person, when it notices something worth sharing:
1. Choose `type`, a 1-line `title`, tags, and a 1–3 line body (a summary/pattern, **no PHI**).
2. **Dedup first:** if an open signal with the same logical key already exists (same slug, `status` ≠ `archived`), **append a tally** to its body (`(count: N)`) and bump `confidence` instead of creating a duplicate. Cross-author dedup: two people noticing the same thing reinforce one signal.
3. Otherwise write a new `signals/<id>.md` with the frontmatter above and `status: new`. Stamp `author` from the current user/agent.

## Consume (symmetric read)
A loop, in its Trigger/Investigate step:
1. Read only the **relevant** signals — filter `signals/*.md` by `status: new|ack` and a `relevance` tag the loop cares about (token-discipline: don't read the whole hub each cycle; grep the frontmatter).
2. On acting on a signal: set `status: acted`, and optionally `TaskCreate` a RICE-scored backlog task (see `${CLAUDE_PLUGIN_ROOT}/commands/backlog-scoring.md`) — signals are **upstream** of the backlog.
3. Set `status: archived` when a signal is resolved or stale so it isn't re-acted forever.

## Lifecycle
`new → ack → acted → archived`. Archived signals stay in git for audit/history but are skipped by consumers and the dashboard's active view.

## Optional: queryable Task mirror
For loops that want fast filtering instead of grep, mirror each signal as a Claude Code Task with `metadata.kind="signal"` (+ the same fields). Files remain the source of truth; the Task mirror is a convenience index and is optional.

## Visualization
Run `${CLAUDE_PLUGIN_ROOT}/bin/signals-build.py` to regenerate `signals/data.js`, `signals/data.json`, and `signals/INDEX.md` from the `signals/*.md` files, then open `templates/signals-dashboard.html` (copy it next to `signals/`) for a live team-status board. Optionally publish it to GitHub Pages (see `.github/workflows/signals-pages.yml`) for a shared team URL — **private repo / non-PHI only**.

## Storage & compliance
- `signals/` is **tracked (committed)** by default — the whole point is team visibility; signals sync via push/pull.
- The PHI-exclusion rule is what makes a *shared* hub safe on a healthcare codebase. It is enforced in `${CLAUDE_PLUGIN_ROOT}/commands/secure.md` and tracked in `${CLAUDE_PLUGIN_ROOT}/compliance/org-controls-audit.md`.
- The generated `data.js` / `data.json` / `INDEX.md` contain only what's already in the (non-PHI) signal files.
