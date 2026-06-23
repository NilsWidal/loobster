#!/usr/bin/env python3
"""
loobster Option D — headroom PostToolUse compression hook.

Reads a Claude Code PostToolUse hook payload on stdin and, *by default (set LOOBSTER_HEADROOM=0 to disable) when a local headroom install is available*, returns an `updatedToolOutput`
that pipes the tool's output through headroom's compressor before it enters the
model's context window. In every other case it passes the output through unchanged.

Install headroom to enable it:  pip install "headroom-ai[code]"  (import name: headroom).

Design rules (see plans/autonomous-loops/00-parent-design-doc.md, slice 6):
  - ENABLED by default. Set LOOBSTER_HEADROOM=0 to disable (e.g. on PHI repos until reviewed).
  - GRACEFUL. Any missing dependency, parse error, or exception -> passthrough.
  - LOCAL-FIRST. headroom runs locally and this hook never logs or persists tool
    output itself. On a PHI repo note two caveats: (a) headroom's CCR store, if
    enabled, keeps originals at rest (your responsibility); (b) headroom's ML
    compressors may download a model from HuggingFace on first use unless
    HF_HUB_OFFLINE=1. Keep LOOBSTER_HEADROOM=0 until headroom has a data-path review.
  - CHEAP. Skips small outputs (below LOOBSTER_HEADROOM_MIN_CHARS, default 2000).

NOTE: headroom's compress() operates on a chat-messages array — compress(messages,
model=...). This hook wraps the single tool output as one user message and extracts
the compressed text back out (string, dict, or messages list). Validate against your
installed headroom-ai version; this path needs a real integration test (the unit
tests mock headroom and can't catch an API mismatch).

Attribution: the compression mechanism is provided by headroom
(https://github.com/headroomlabs-ai/headroom). This hook is glue, not a reimplementation.
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


def _result_text(result):
    """Pull compressed text out of headroom's return — str, dict, or messages list."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        if isinstance(result.get("content"), str):
            return result["content"]
        result = result.get("messages", result)
    if isinstance(result, list) and result:
        last = result[-1]
        if isinstance(last, str):
            return last
        if isinstance(last, dict):
            content = last.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):  # content blocks: [{type,text}, ...]
                return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return None


def main():
    # 1. Enabled by default; LOOBSTER_HEADROOM=0 disables (e.g. PHI repos pre-review).
    if os.environ.get("LOOBSTER_HEADROOM", "1") in ("0", "false", "off"):
        _passthrough()

    # 2. Read the hook payload.
    try:
        payload = json.load(sys.stdin)
    except Exception:
        _passthrough()

    tool_response = payload.get("tool_response")
    text = _extract_text(tool_response)
    if not text:
        _passthrough()

    # 3. Skip small outputs — compression overhead isn't worth it.
    try:
        min_chars = int(os.environ.get("LOOBSTER_HEADROOM_MIN_CHARS", "2000"))
    except ValueError:
        min_chars = 2000
    if len(text) < min_chars:
        _passthrough()

    # 4. Capability-detect headroom. Absent -> passthrough.
    try:
        from headroom import compress  # type: ignore
    except Exception:
        _passthrough()

    # 5. Compress. headroom.compress operates on a messages array; wrap the single
    #    tool output as one message and pull the compressed text back out. Any
    #    failure -> passthrough (never break the tool flow).
    try:
        model = os.environ.get("LOOBSTER_HEADROOM_MODEL", "claude-opus-4-8")
        result = compress([{"role": "user", "content": text}], model=model)
        compressed = _result_text(result)
        if not isinstance(compressed, str) or not compressed or len(compressed) >= len(text):
            _passthrough()
    except Exception:
        _passthrough()

    # 6. Substitute the compressed text for what the model sees.
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
