# RePPIT Health

A Claude Code plugin that runs a secure development workflow for healthcare software.

**RePPIT Health** implements the **RePPITS** methodology, **R**esearch, **P**ropose, **P**lan, **I**mplement, **T**est, **S**ecure, extending the [RePPIT framework](https://themodernsoftware.dev) by [Mihail Eric](https://github.com/mihail911) (Head of AI, creator of Stanford's first AI software engineering course) with HIPAA, SOC2, and HITRUST compliance gates for healthcare and healthtech teams.

## What you get

Seven slash commands, available in Claude Code, Cursor, and any client that supports the Claude Code plugin spec:

| Command | What it does |
|---|---|
| `/reppit <topic-or-issue>` | Run the full Research → Propose → Plan → Implement → Test → Secure workflow, with explicit approval gates between phases |
| `/research-codebase` | Document the existing codebase exactly as it is today (no suggestions, no RCA) |
| `/make-proposals` | Generate up to two solution proposals grounded in research |
| `/make-plan` | Break the chosen proposal into ordered Linear issues (or local `plans/*.md` if Linear MCP is not configured) |
| `/implement <issue>` | Implement a single Linear issue, with optional Ralph Loop mode |
| `/review-code` | Review all uncommitted changes, post findings to Linear |
| `/secure` | Run HIPAA, SOC2, and HITRUST checklists against your diff, separating code-verifiable findings from organizational controls |

```
Research --> Propose --> Plan --> Implement --> Test --> Secure --> Done
   ^            ^          ^         ^           ^         |
   | refine     | refine   | refine  | fix loop  | fix     |
   └────┘       └────┘     └────┘    └────┘      └──┘      |
                                          ^                 |
                                          └── fix & test ───┘
```

## Install

### From the plugin marketplace (recommended)

In Claude Code (≥ 1.0.33):

```
/plugin marketplace add carainc/reppit-health
/plugin install reppit-health@carainc-reppit-health
```

That's it. The slash commands are immediately available.

### From a local clone

```bash
git clone https://github.com/carainc/reppit-health.git
```

Then in Claude Code:

```
/plugin marketplace add ./reppit-health
/plugin install reppit-health@carainc-reppit-health
```

Useful for trying changes before pushing.

## Quick start

In any project directory:

```
/reppit Add a patient intake form
```

or with a Linear issue:

```
/reppit CAR-123
```

The plugin walks Research → Propose → Plan → Implement → Test → Secure and pauses at each gate for your approval. You can also invoke any phase directly, e.g. `/secure` to audit current uncommitted changes without running the full flow.

## Compliance checklists

Checklists live in `compliance/` inside the installed plugin:

- **`hipaa-checklist.md`** — Administrative, physical, and technical safeguards (§164.308-312), PHI detection, minimum necessary, BAA verification, breach notification, telehealth compliance
- **`soc2-checklist.md`** — All Trust Service Criteria (CC1-CC9), Availability (A1), Confidentiality (C1), Processing Integrity (PI1), Privacy (P1), plus injection prevention and secrets management
- **`hitrust-checklist.md`** — All 14 CSF v11 control categories (00-13): access control, risk management, encryption, operations, incident management, business continuity, privacy practices, cross-tenant isolation
- **`org-controls-audit.md`** — Schedule and tracking for organizational controls that can't be verified from code alone

Each item gets a PASS / WARN / FAIL / SKIPPED status. Items marked `[org]` (physical safeguards, board oversight, BAAs with subprocessors) are surfaced separately so they don't get auto-passed by a green diff.

### Per-workspace overrides

If you want to customize a checklist for a specific repo, drop a file at `.claude/compliance/<framework>-checklist.md` in that workspace. `/secure` reads workspace overrides first, then falls back to the plugin's defaults.

## Linear integration (optional)

If the [Linear MCP](https://linear.app/docs/mcp) is configured in Claude Code, the plugin will:

- Read issues mentioned in `/implement <issue-id>`
- Save research and proposal documents as Linear documents
- Create parent + sub-issue structures during `/make-plan`
- Post review and security findings as comments on the relevant issue

If Linear is not configured, the plugin falls back to local `.md` files in `research/`, `plans/`, and the conversation transcript. Both modes work end-to-end.

## Credits

- **RePPIT methodology** — [Mihail Eric](https://github.com/mihail911), Head of AI, creator of [Stanford's first AI software engineering course](https://themodernsoftware.dev)
- **RePPIT Health plugin** — [Cara](https://caramedical.com)

## License

Apache 2.0, see [LICENSE](LICENSE).
