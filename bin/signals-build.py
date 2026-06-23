#!/usr/bin/env python3
"""
signals-build — regenerate the signals dashboard data from the signal files.

Scans a signals/ directory of `<id>.md` files (frontmatter + body), and writes:
  - signals/data.js    window.SIGNALS = [...]   (loads from file:// — dashboard)
  - signals/data.json  the same array            (fetch/poll when served / Pages)
  - signals/INDEX.md    human-readable table of active signals

Dependency-free (no PyYAML). Malformed files are skipped with a warning.

A lightweight **best-effort PHI lint** (NOT a guarantee — see README/signals.md)
flags signal content that looks like raw PHI; signals must be non-PHI summaries
because the hub is committed + shared. By default, PHI-flagged signals are
**quarantined** — excluded from the generated artifacts so they don't get
committed — unless you pass --allow-flagged. With --strict, any malformed or
PHI-shaped signal makes the build exit non-zero (for CI / the Secure phase).

Usage:
  signals-build.py [signals_dir] [--strict] [--allow-flagged]
    signals_dir       directory of <id>.md signal files (default: ./signals)
    --strict          exit 1 if any signal is malformed or PHI-shaped
    --allow-flagged   include PHI-flagged signals in the output (default: quarantine)
    -h, --help        show this help and exit
"""
import json
import os
import re
import sys

REQUIRED = ("id", "author", "type", "status", "title")

# PHI-shaped patterns — a best-effort lint, not enforcement. Signals must be
# non-PHI summaries; this catches common shapes but cannot catch every name.
PHI_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "SSN-like"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "email"),
    (re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "phone-like"),
    (re.compile(r"\b(DOB|date of birth|MRN)\b", re.I), "DOB/MRN"),
    # "patient jane" / "patient Jane" — case-insensitive on the name now.
    (re.compile(r"\bpatient\s+[A-Za-z][a-z]+\b", re.I), "named patient"),
    # Honorific + name: "Mr. Smith", "Dr Jones", "Mrs. Lopez".
    (re.compile(r"\b(?:Mr|Mrs|Ms|Mx|Dr|Doctor|Mister|Miss)\.?\s+[A-Z][a-z]+\b"), "named person"),
    # An identifier referenced as a record/member/chart/account number.
    (re.compile(r"\b(?:record|member|chart|account|patient|case)\s*(?:no\.?|number|num|#|id)\s*[:#-]?\s*\d{3,}", re.I),
     "record/member id"),
    # A bare long numeric id (>= 7 digits) — likely an MRN/member number.
    (re.compile(r"\b\d{7,}\b"), "long numeric id"),
]


def parse_frontmatter(text):
    """Return (meta dict, body) or (None, None) if no valid frontmatter."""
    if not text.startswith("---"):
        return None, None
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return None, None
    fm = parts[0][3:].strip("\n")
    # The split already consumed the closing `\n---` fence, so the remainder is
    # the body — strip surrounding whitespace only (do NOT strip leading list
    # markers, which corrupts a body that starts with a bullet).
    body = parts[1].strip()
    meta = {}
    for line in fm.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            meta[key] = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
        else:
            meta[key] = val.strip("'\"")
    return meta, body


def phi_hits(text):
    return sorted({label for rx, label in PHI_PATTERNS if rx.search(text or "")})


def _relevance_tags(value):
    """Render relevance whether it's a list or a scalar string."""
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def main():
    argv = sys.argv[1:]
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return

    strict = "--strict" in argv
    allow_flagged = "--allow-flagged" in argv
    positionals = [a for a in argv if not a.startswith("-")]
    signals_dir = positionals[0] if positionals else "signals"

    if not os.path.isdir(signals_dir):
        # No hub here — do nothing. Never write artifacts into an unrelated cwd.
        print(f"signals-build: no signals dir at '{signals_dir}' — nothing to do")
        sys.exit(0)

    signals, skipped, phi_flagged = [], [], []
    for name in sorted(os.listdir(signals_dir)):
        if not name.endswith(".md") or name.upper() in ("INDEX.MD", "README.MD"):
            continue
        path = os.path.join(signals_dir, name)
        try:
            text = open(path, encoding="utf-8").read()
        except Exception:
            skipped.append(name)
            continue
        meta, body = parse_frontmatter(text)
        if not meta or any(k not in meta for k in REQUIRED):
            skipped.append(name)
            print(f"  skip (malformed): {name}")
            continue
        hits = phi_hits(f"{meta.get('title','')} {body}")
        if hits:
            phi_flagged.append((name, hits))
            disposition = "included (--allow-flagged)" if allow_flagged else "QUARANTINED"
            print(f"  PHI-shaped ({', '.join(hits)}) -> {disposition}: {name}")
            if not allow_flagged:
                continue  # quarantine: keep it out of committed artifacts
        meta["body"] = body
        signals.append(meta)

    print(f"signals-build: {len(signals)} signal(s) written, "
          f"{len(skipped)} skipped, {len(phi_flagged)} PHI-flagged"
          f"{'' if allow_flagged else ' (quarantined)'}")
    if strict and (skipped or phi_flagged):
        sys.exit(1)

    os.makedirs(signals_dir, exist_ok=True)
    payload = json.dumps(signals, indent=2, ensure_ascii=False)
    with open(os.path.join(signals_dir, "data.json"), "w", encoding="utf-8") as f:
        f.write(payload + "\n")
    with open(os.path.join(signals_dir, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.SIGNALS = " + payload + ";\n")
    _write_index(signals_dir, signals)
    print(f"  wrote {signals_dir}/data.js, data.json, INDEX.md")


def _write_index(out_dir, signals):
    active = [s for s in signals if s.get("status") != "archived"]
    lines = ["# Signals — active\n",
             f"_{len(active)} active of {len(signals)} total. Generated by `bin/signals-build.py`._\n",
             "| Status | Type | Author | Source | Title | Tags |",
             "|---|---|---|---|---|---|"]
    for s in sorted(active, key=lambda x: (x.get("status", ""), x.get("id", ""))):
        tags = ", ".join(_relevance_tags(s.get("relevance")))
        lines.append(f"| {s.get('status','')} | {s.get('type','')} | {s.get('author','')} "
                     f"| {s.get('source','')} | {s.get('title','')} | {tags} |")
    with open(os.path.join(out_dir, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
