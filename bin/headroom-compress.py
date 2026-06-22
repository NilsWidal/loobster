#!/usr/bin/env python3
"""
loobster Option D — headroom PostToolUse compression hook.

Reads a Claude Code PostToolUse hook payload on stdin and, *by default (set LOOBSTER_HEADROOM=0 to disable) when a local headroom install is available*, returns an `updatedToolOutput`
that pipes the tool's output through headroom's compressor before it enters the
model's context window. In every other case it passes the output through unchanged.

Design rules (see plans/autonomous-loops/00-parent-design-doc.md, slice 6):
  - ENABLED by default. Set LOOBSTER_HEADROOM=0 to disable (e.g. on PHI repos until reviewed).
  - GRACEFUL. Any missing dependency, parse error, or exception -> passthrough.
  - LOCAL ONLY. Uses headroom's local `compress` (no network); never logs or
    persists tool output itself. headroom's own CCR store (if the user enables it)
    is the user's responsibility and is PHI-at-rest — see the README PHI caveat.
  - CHEAP. Skips small outputs (below LOOBSTER_HEADROOM_MIN_CHARS, default 2000).

Attribution: the compression mechanism is provided by headroom
(https://github.com/chopratejas/headroom). This hook is glue, not a reimplementation.
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

    # 5. Compress. Any failure -> passthrough (never break the tool flow).
    try:
        model = os.environ.get("LOOBSTER_HEADROOM_MODEL", "claude-opus-4-8")
        compressed = compress(text, model=model)
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
