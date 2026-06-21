# Security frameworks — enable / disable

RePPIT's Secure phase is **framework-agnostic**: healthcare (HIPAA, HITRUST) is *one aspect*, not the whole tool. You choose which frameworks `/secure` runs against your diff. Supported today:

| Key | Framework | Typical use |
|---|---|---|
| `hipaa` | HIPAA Security Rule | US healthcare / PHI |
| `hitrust` | HITRUST CSF | Healthcare, vendor assurance |
| `iso27001` | ISO/IEC 27001:2022 (Annex A) | General infosec / international |
| `soc2` | SOC 2 Trust Service Criteria | SaaS / B2B trust |

Each has a checklist in `compliance/<key>-checklist.md`.

## How to configure
Create `.claude/reppit-frameworks.json` in your **workspace** (the repo you run `/secure` in):

```json
{ "frameworks": ["soc2", "iso27001"] }
```

`/secure` runs **only** the listed frameworks. If the file is absent, the default is **all four** (conservative — nothing is silently skipped).

## Profiles (suggested starting points)
- **Healthcare:** `["hipaa", "hitrust", "soc2"]`
- **General SaaS:** `["soc2", "iso27001"]`
- **International / enterprise:** `["iso27001", "soc2"]`
- **Everything:** `["hipaa", "hitrust", "iso27001", "soc2"]` (default)

Copy one into `.claude/reppit-frameworks.json` and edit.

## Per-repo checklist overrides
You can also tailor a framework's checklist for a repo: drop `.claude/compliance/<key>-checklist.md` in your workspace and `/secure` prefers it over the plugin's built-in. (Independent of which frameworks are *enabled*.)

## Notes
- Enabling fewer frameworks does not disable the workflow's other safety rails (tier gates, the autonomous-loop cap, the no-PHI-in-signals rule).
- `[org]` items in each checklist are organizational controls tracked in `org-controls-audit.md`, regardless of which frameworks are enabled.
