---
name: token-discipline
description: Reference only (do NOT invoke as an action): token-reduction conventions (subagent isolation, artifact compaction). Applied throughout the other skills.
---

<!-- GENERATED from reference/token-discipline.md by bin/build-codex-skills.py — do not edit here. -->

# Token discipline — native context conventions for RePPITS

Shared conventions that keep token usage low *without* any runtime dependency, so they work identically in Claude Code, the plugin, and a custom Agent SDK harness. These are the always-on **Option A** practices referenced by the phase commands. They reduce tokens by **elimination and structure**, not by wire-level compression.

> Attribution: these conventions adapt the *mechanisms* pioneered by [headroom](https://github.com/headroomlabs-ai/headroom) (headroomlabs-ai/headroom) — reversible-context retrieval, prefix stability, and compressing what the model reads — to a runtime-free, prompt-level form. For real wire-level compression (AST-aware code/JSON compressors, the kompress prose model), see the Option D hook and the Option C proxy/SDK-middleware recipe in the README.

## 1. Subagent isolation (the biggest lever)
When a step must read a lot to produce a little — codebase research, reviewing a wide diff, evaluating checklists across many files — delegate the heavy reading to a subagent (`Agent` / `Explore`) and bring back only the **conclusion**.

- The subagent burns its own context window reading 10k–100k tokens; the main thread receives only the synthesized result (a summary, a findings list, a verdict).
- This is *elimination*, not lossy compression: the subagent saw the full content; the main thread never pays for the raw bytes.
- Use it when you need the answer, not the raw material. If you'll need the raw bytes again later, have the subagent write them to a file (see §2) rather than returning them.

## 2. Artifact compaction (reversible by construction)
Write large intermediate outputs to disk, then carry only a short summary forward; re-read the file on demand.

- Research → `research/`, plans → `plans/`, reviews/security reports → the issue/Task or a file. These already exist in the flow — the discipline is to **pass the summary between phases, not the full document**, and to re-open the file only when a later phase truly needs the detail.
- This is the runtime-free analog of headroom's reversible-context retrieval: the original is losslessly on disk and fully recoverable; the "retrieve" step is just re-reading the file.

## 3. Cache-stable prefixes
Don't gratuitously rewrite stable context (the orchestration preamble, system conventions, large unchanged artifacts) between phases. Append rather than reorder/rewrite so provider prompt caches keep hitting. (A markdown plugin can't actively align prefixes the way a proxy does — this only avoids *breaking* cache hits the harness would otherwise get.)

## 4. Terse output + effort routing
- Default to concise output: no preamble, no restating the question, tables over prose where it's denser.
- On routine/mechanical steps, prefer lower reasoning effort; reserve deep effort for the hard judgment (proposal design, adversarial Secure verification).

## Ceiling (be honest)
These conventions cover the reads you deliberately route through a subagent or a file. They do **not** compress large raw blobs that must stay live in the main context, and they are advisory (the orchestrator must actually follow them). For automatic, every-read compression, Option D is on by default in Claude Code — a built-in pure-stdlib crusher (`bin/lite_crush.py`, zero install) with an optional headroom upgrade (`pip install "headroom-ai[code]"`) — or run headroom as a proxy/SDK middleware (Option C) outside Claude Code.
