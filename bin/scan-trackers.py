#!/usr/bin/env python3
"""
scan-trackers — detect third-party tracking / advertising / analytics scripts in a
web app's source, so the Secure phase can flag them.

WHY THIS MATTERS (compliance): loading a third-party tracker (Google Ads/AdSense,
Google Analytics / GTM, Meta Pixel, etc.) on a page that handles PHI sends data to
that vendor. Per HHS OCR's guidance on online tracking technologies, doing so
without a signed BAA (and without keeping PHI out of what's sent) is a HIPAA
violation — the basis of the Meta Pixel / Google Analytics healthcare settlements.
Outside healthcare it's still a SOC 2 / ISO 27001 / privacy concern (consent,
cookie disclosure, data-processing agreements).

This is a best-effort lint (signature match), not proof. It reports what it finds;
the Secure phase decides PASS/WARN/FAIL given whether the repo handles PHI.

Usage:
  scan-trackers.py [path ...] [--strict] [--json]
    path        files or directories to scan (default: .)
    --strict    exit 1 if any tracker is found (for CI / the Secure gate)
    --json      machine-readable output
    -h, --help  show this help

Exit codes: 0 = ok (or findings, non-strict) · 1 = findings with --strict · 2 = usage
"""
import json
import os
import re
import sys

SCAN_EXT = {".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
            ".vue", ".svelte", ".astro", ".php", ".erb", ".hbs", ".ejs"}
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".next", "out", "vendor",
             ".loobster", "coverage", "__pycache__"}

# (label, category, compiled pattern). Categories: ads | analytics | session | tag-manager
TRACKERS = [
    ("Google Tag Manager", "tag-manager", re.compile(r"googletagmanager\.com|GTM-[A-Z0-9]{4,}")),
    ("Google Analytics / gtag", "analytics", re.compile(r"google-analytics\.com|gtag\s*\(|\bga\s*\(\s*['\"]|\bUA-\d{4,}|\bG-[A-Z0-9]{8,}")),
    ("Google Ads / AdSense", "ads", re.compile(r"googlesyndication\.com|googleadservices\.com|googleads\.|\bAW-\d{6,}|google_conversion")),
    ("DoubleClick", "ads", re.compile(r"doubleclick\.net")),
    ("Meta / Facebook Pixel", "ads", re.compile(r"connect\.facebook\.net|\bfbq\s*\(")),
    ("TikTok Pixel", "ads", re.compile(r"analytics\.tiktok\.com|\bttq\.(?:load|page|track)\b")),
    ("LinkedIn Insight", "ads", re.compile(r"snap\.licdn\.com|_linkedin_partner_id")),
    ("Twitter/X Pixel", "ads", re.compile(r"static\.ads-twitter\.com|\btwq\s*\(")),
    ("Hotjar", "session", re.compile(r"static\.hotjar\.com|\bhj\s*\(")),
    ("FullStory", "session", re.compile(r"fullstory\.com|\bFS\.(?:identify|event)\b")),
    ("Microsoft Clarity", "session", re.compile(r"clarity\.ms|\bclarity\s*\(")),
    ("Segment", "analytics", re.compile(r"cdn\.segment\.com|analytics\.(?:load|track|identify)\s*\(")),
    ("Mixpanel", "analytics", re.compile(r"\bcdn\.mxpnl\.com|mixpanel\.(?:init|track)\b")),
    ("Amplitude", "analytics", re.compile(r"amplitude\.com/libs|amplitude\.(?:getInstance|init)\b")),
]


def iter_files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for name in files:
                    if os.path.splitext(name)[1].lower() in SCAN_EXT:
                        yield os.path.join(root, name)


def scan(paths):
    findings = []
    for path in iter_files(paths):
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    for label, category, rx in TRACKERS:
                        if rx.search(line):
                            findings.append({
                                "file": path, "line": lineno,
                                "tracker": label, "category": category,
                                "snippet": line.strip()[:120],
                            })
        except OSError:
            continue
    return findings


def main():
    argv = sys.argv[1:]
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0
    strict = "--strict" in argv
    as_json = "--json" in argv
    paths = [a for a in argv if not a.startswith("-")] or ["."]

    findings = scan(paths)

    if as_json:
        print(json.dumps(findings, indent=2))
    elif not findings:
        print("scan-trackers: no third-party trackers found")
    else:
        print(f"scan-trackers: {len(findings)} third-party tracker reference(s) found:")
        for f in findings:
            print(f"  {f['file']}:{f['line']}  [{f['category']}] {f['tracker']}")
        print("\nIf this app handles PHI: a tracker on a PHI page needs a signed BAA and "
              "must not transmit PHI (HHS OCR online-tracking guidance) — otherwise FAIL.")

    if strict and findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
