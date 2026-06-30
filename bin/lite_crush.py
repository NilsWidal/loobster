#!/usr/bin/env python3
"""
loobster lite-crush — a small, dependency-free, deterministic tool-output crusher.

This is the ALWAYS-ON, zero-install fallback tier for the Option D headroom hook
(bin/headroom-compress.py). headroom's real compressors (SmartCrusher / CodeCompressor)
are a compiled Rust extension (`headroom._core`, built with maturin) plus a tiktoken +
pydantic framework — they CANNOT be embedded as pure Python, so they require
`pip install headroom-ai`. When that package is present the hook prefers it; when it
is absent this module runs instead so compression still happens with nothing installed.

Design rules:
  - PURE STDLIB. No third-party imports, no network, no model downloads, no disk writes.
  - DETERMINISTIC. Same input → same output. No randomness, no clocks.
  - CONSERVATIVE & MARKED. Lossless where possible (whitespace, JSON minify). Lossy
    edits (collapsing repeated lines, clamping huge lines) are explicitly marked with a
    `[loobster-crush: …]` token so the model never sees silent truncation.
  - SELF-GUARDING. Every transform only applies when it actually saves bytes; crush()
    returns the original string unchanged if the net result isn't smaller.

It is NOT a reimplementation of headroom — it is a lightweight crusher inspired by the
same idea (compress what the model reads). It pays off most on logs, repetitive output,
and JSON; it does little to prose or source code (which is honest and expected).

Attribution: the "compress what the model reads" approach is from headroom
(https://github.com/headroomlabs-ai/headroom, Apache-2.0). This module shares none of
its code; it is an independent, much smaller implementation.
"""
from __future__ import annotations

import json
import re

MARKER = "[loobster-crush: {note}]"

# Defaults — overridable per call. Chosen so a transform never fires unless it saves.
DUP_MIN = 3        # collapse a run of >= this many identical consecutive lines
BLANK_MAX = 1      # max consecutive blank lines to keep
LINE_MAX = 2000    # clamp single lines longer than this
LINE_KEEP = 600    # chars to keep from each end of a clamped line


def _marker(note: str) -> str:
    return MARKER.format(note=note)


def _minify_json(text: str):
    """If the whole text is one JSON document, return a compact (lossless) re-dump.

    Returns the compact string, or None if the text isn't a single JSON value.
    Whitespace between tokens is dropped; the data is preserved.
    """
    stripped = text.strip()
    if not stripped or stripped[0] not in "{[":
        return None
    try:
        obj = json.loads(stripped)
    except (ValueError, RecursionError):
        return None
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def _collapse_runs(lines, dup_min: int, blank_max: int):
    """Collapse runs of identical lines and runs of blank lines. Each collapse only
    applies when it removes bytes; otherwise the run is emitted verbatim."""
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        j = i + 1
        while j < n and lines[j] == line:
            j += 1
        run = j - i  # number of identical consecutive `line`s

        if line == "":
            # Blank-line run → keep at most blank_max blanks.
            out.extend([""] * min(run, blank_max))
        elif run >= dup_min:
            marker = _marker(f"previous line repeated x{run}")
            # Only collapse if "line + marker" is smaller than the original run.
            original = run * (len(line) + 1)
            collapsed = len(line) + 1 + len(marker) + 1
            if collapsed < original:
                out.append(line)
                out.append(marker)
            else:
                out.extend([line] * run)
        else:
            out.extend([line] * run)
        i = j
    return out


def _clamp_long_lines(lines, line_max: int, line_keep: int):
    out = []
    for line in lines:
        if len(line) > line_max:
            elided = len(line) - 2 * line_keep
            marker = _marker(f"+{elided} chars elided")
            candidate = line[:line_keep] + marker + line[-line_keep:]
            out.append(candidate if len(candidate) < len(line) else line)
        else:
            out.append(line)
    return out


def crush(
    text,
    *,
    dup_min: int = DUP_MIN,
    blank_max: int = BLANK_MAX,
    line_max: int = LINE_MAX,
    line_keep: int = LINE_KEEP,
    json_minify: bool = True,
) -> str:
    """Return a deterministically crushed copy of `text`, or `text` unchanged if no
    transform produces a smaller result. Always returns a str; never raises on str input."""
    if not isinstance(text, str) or not text.strip():
        return text

    # 1) Whole-document JSON minify (lossless). Wins big on pretty-printed payloads.
    if json_minify:
        compact = _minify_json(text)
        if compact is not None and len(compact) < len(text):
            return compact

    # 2) Line-oriented transforms. Preserve whether the text ended with a newline.
    trailing_nl = text.endswith("\n")
    lines = text.split("\n")
    if trailing_nl:
        lines = lines[:-1]  # drop the empty element split() adds for a trailing \n

    lines = [re.sub(r"[ \t]+$", "", ln) for ln in lines]   # strip trailing whitespace
    lines = _collapse_runs(lines, dup_min, blank_max)
    lines = _clamp_long_lines(lines, line_max, line_keep)

    result = "\n".join(lines)
    if trailing_nl:
        result += "\n"

    return result if len(result) < len(text) else text


if __name__ == "__main__":  # tiny CLI for manual/integration testing: crush stdin -> stdout
    import sys

    sys.stdout.write(crush(sys.stdin.read()))
