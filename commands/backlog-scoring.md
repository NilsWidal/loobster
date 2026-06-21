# Backlog scoring — sophisticated, model-set prioritization

How the goal-loop (`/reppit-loop`) and `/make-plan` score and re-score backlog items so the loop always works the highest-leverage task. Scores live in each Claude Code Task's `metadata` (the backlog source of truth).

## Model: RICE
For each backlog item the model estimates four factors and computes a score:

```
score = (reach × impact × confidence) / effort
```

| Factor | Meaning | Scale |
|---|---|---|
| **reach** | How much of the goal / how many users/files/cases this item moves | 1–10 (relative) |
| **impact** | How strongly it advances the goal when done | 0.25, 0.5, 1, 2, 3 (massive) |
| **confidence** | How sure we are about reach × impact | 0.5 (low), 0.8 (med), 1.0 (high) |
| **effort** | Estimated cost to complete (person-equiv units) | ≥ 0.5 |

The estimates are **model-set** (the model fills them from the item description + investigation), and **user-overridable** — if the user sets any factor, keep it and don't overwrite it on re-score.

## Where it's stored
On each Task, in `metadata`:
```
metadata: {
  goalId, reach, impact, confidence, effort,
  score,            // recomputed; (reach*impact*confidence)/effort
  scoreSource,      // "model" | "user" per factor that was overridden
  cycle,            // cycle last scored
  learnings         // rolling 1-line digest from the last attempt
}
```

## When scoring happens
- **Initial** — when items enter the backlog (`/make-plan` during a goal run, or backlog-gen inside the loop). Set all four factors + `score`.
- **Re-score** — every *Review & learn* step: update factors from what the last cycle taught (e.g. an item that proved harder gets higher `effort`; a newly-found high-leverage gap gets high `reach`/`impact`), recompute `score`. **Never overwrite a user-set factor.**
- **Selection** — the loop's "next item" trigger picks the highest `score` among open, unblocked tasks for the active `goalId`.

## Notes
- Keep estimates cheap — this is prioritization, not precision. A 1-line rationale per factor is enough; do not write essays into metadata.
- Ties broken by lowest `effort` (smaller wins first), then lowest Task id.
- Blocked tasks (open `blockedBy`) are never selected regardless of score.
