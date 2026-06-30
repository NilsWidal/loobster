#!/usr/bin/env python3
"""
loobster Option D — token-compression PostToolUse hook (two tiers).

Reads a Claude Code PostToolUse hook payload on stdin and returns an
`updatedToolOutput` that shrinks a tool's output before it enters the model's context
window. It is ENABLED by default (set LOOBSTER_HEADROOM=0 to disable, e.g. on PHI repos
until reviewed) and compresses in two tiers:

  Tier 1 — real headroom, if installed. `pip install "headroom-ai[code]"` ships the
           genuine compressors (a compiled Rust extension `headroom._core` + tiktoken +
           pydantic). headroom's real mechanics CANNOT be embedded as pure Python, so
           this tier only runs when the package is importable. Preferred when present.
  Tier 2 — lite-crush, always available. A small, pure-stdlib, deterministic crusher
           (bin/lite_crush.py) — no install, no network, no model. Runs whenever Tier 1
           is absent or didn't help. This is what makes compression work out of the box.
  Else   — passthrough (original output unchanged).

Design rules (see plans/autonomous-loops/00-parent-design-doc.md, slice 6):
  - ENABLED by default. LOOBSTER_HEADROOM=0 disables BOTH tiers. LOOBSTER_LITE_CRUSH=0
    disables only Tier 2 (keep headroom-only behavior).
  - GRACEFUL. Any missing dependency, parse error, or exception -> passthrough; a Tier 1
    failure falls through to Tier 2; never breaks the tool flow.
  - LOCAL-FIRST. Both tiers run locally and this hook never logs or persists tool output.
    PHI note: because it is on by default, tool outputs (possible PHI) flow through a
    compressor whenever this hook fires — Tier 2 is first-party and pure-local; Tier 1
    adds a third party (headroom) to the data path. headroom's ML compressors may also
    download a model from HuggingFace on first use unless HF_HUB_OFFLINE=1. Keep
    LOOBSTER_HEADROOM=0 until the data path has had a review on PHI repos.
  - CHEAP. Skips small outputs (below LOOBSTER_HEADROOM_MIN_CHARS, default 2000).

headroom's compress() returns a CompressResult object (`.messages`, `.tokens_saved`,
`.compression_ratio`); `_headroom_text` extracts the compressed text from `.messages`
(and still tolerates str/dict/list shapes for older versions and test mocks).

Attribution: Tier 1's compression is provided by headroom
(https://github.com/headroomlabs-ai/headroom, Apache-2.0) — this hook is glue, not a
reimplementation. Tier 2 (lite_crush) is independent loobster code inspired by the same
"compress what the model reads" idea; it shares none of headroom's source.
"""
import json
import os
import sys


def _passthrough():
    """Emit nothing; Claude Code keeps the original tool output."""
    sys.exit(0)


def _extract_text(tool_response):
    """Best-effort: pull a compressible string out of the tool_response field."""
    if isinstance(tool_response, str):
        return tool_response
    if isinstance(tool_response, dict):
        for key in ("output", "stdout", "content", "text", "result"):
            val = tool_response.get(key)
            if isinstance(val, str) and val:
                return val
    return None


def _message_text(messages):
    """Pull the text content out of a messages list (last message)."""
    if isinstance(messages, list) and messages:
        last = messages[-1]
        content = last.get("content") if isinstance(last, dict) else last
        if isinstance(content, str):
            return content
        if isinstance(content, list):  # content blocks: [{type,text}, ...]
            return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return None


def _headroom_text(result):
    """Pull compressed text out of headroom's return value.

    Real headroom-ai returns a CompressResult object exposing `.messages`. We also
    accept a bare messages list, a plain string, or a dict (older versions / test mocks).
    """
    messages = getattr(result, "messages", None)
    if messages is None:
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            if isinstance(result.get("content"), str):
                return result["content"]
            messages = result.get("messages")
        elif isinstance(result, list):
            messages = result
    text = _message_text(messages)
    if text is not None:
        return text
    return result if isinstance(result, str) else None


def _shorter(candidate, original):
    return isinstance(candidate, str) and candidate and len(candidate) < len(original)


def _headroom_compress(text):
    """Tier 1: real headroom if importable. Returns compressed str or None."""
    try:
        from headroom import compress  # type: ignore
    except Exception:
        return None
    try:
        model = os.environ.get("LOOBSTER_HEADROOM_MODEL", "claude-opus-4-8")
        result = compress([{"role": "user", "content": text}], model=model)
        return _headroom_text(result)
    except Exception:
        return None


def _lite_compress(text):
    """Tier 2: pure-stdlib lite-crush. Returns compressed str or None."""
    if os.environ.get("LOOBSTER_LITE_CRUSH", "1") in ("0", "false", "off"):
        return None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from lite_crush import crush  # type: ignore
        return crush(text)
    except Exception:
        return None


def main():
    # 1. Enabled by default; LOOBSTER_HEADROOM=0 disables both tiers.
    if os.environ.get("LOOBSTER_HEADROOM", "1") in ("0", "false", "off"):
        _passthrough()

    # 2. Read the hook payload.
    try:
        payload = json.load(sys.stdin)
    except Exception:
        _passthrough()

    text = _extract_text(payload.get("tool_response"))
    if not text:
        _passthrough()

    # 3. Skip small outputs — compression overhead isn't worth it.
    try:
        min_chars = int(os.environ.get("LOOBSTER_HEADROOM_MIN_CHARS", "2000"))
    except ValueError:
        min_chars = 2000
    if len(text) < min_chars:
        _passthrough()

    # 4. Tier 1 (headroom) preferred; fall through to Tier 2 (lite-crush).
    compressed = _headroom_compress(text)
    if not _shorter(compressed, text):
        compressed = _lite_compress(text)
    if not _shorter(compressed, text):
        _passthrough()

    # 5. Substitute the compressed text for what the model sees.
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": compressed,
        }
    }
    json.dump(out, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Absolute backstop: never let this hook break a tool call.
        sys.exit(0)
