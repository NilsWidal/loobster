# RePPITHealth

AI-powered development workflow for healthcare software with built-in compliance gates.

**RePPIT** (Research, Propose, Plan, Implement, Test) is a structured development methodology created by [Mikhail Eric](https://github.com/mikhailejohneric) (Stanford lecturer and researcher). **RePPITHealth** extends it with HIPAA, SOC2, and HITRUST compliance checks for healthcare and healthtech teams.

## What it does

A VS Code / Cursor sidebar extension that guides you through a complete development workflow powered by Claude Code:

```
Research  -->  Propose  -->  Plan  -->  Implement  -->  Review  -->  Compliance  -->  Done
    ^              ^            ^           ^              ^             ^
    |  refine      |  refine    |  refine   |   fix loop   |   fix loop  |  fix loop
    └──────┘       └──────┘     └──────┘    └─────────┘    └─────────┘   └─────────┘
```

Each phase has a **gate** — the workflow pauses, plays a sound, and waits for your approval before advancing. You can refine any phase as many times as needed.

## Features

- **Visual sidebar** — phase stepper, gate buttons, real-time Claude output log
- **Compliance gates** — HIPAA, SOC2, HITRUST checklists run against your diff before commit
- **Linear integration** (optional) — creates issues, documents, and comments in Linear. Falls back to local `.md` files if Linear is not configured
- **Sound notifications** — plays a sound when your input is needed
- **Works in VS Code and Cursor**

## Quick start

1. Install the extension
2. Open command palette: `RePPIT: Initialize Project Templates`
3. Open the RePPITHealth sidebar
4. Click **Start Workflow** or run `RePPIT: Start Workflow` from the command palette

### Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- Node.js 18+

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `reppithealth.notifications.sound` | `true` | Play sound at gates |
| `reppithealth.notifications.system` | `true` | Show system notifications |
| `reppithealth.compliance.hipaa` | `true` | Enable HIPAA checks |
| `reppithealth.compliance.soc2` | `false` | Enable SOC2 checks |
| `reppithealth.compliance.hitrust` | `false` | Enable HITRUST checks |
| `reppithealth.claudePath` | `claude` | Path to Claude CLI |
| `reppithealth.autoApprove` | `false` | Skip Claude tool approval prompts |

## How it works

The extension spawns the Claude CLI as a child process and communicates via structured markers. Your `.claude/commands/*.md` files define the behavior of each phase — you can customize them per project.

### Phases

1. **Research** — Claude explores your codebase and documents findings
2. **Propose** — generates 2 solution proposals with trade-offs
3. **Plan** — breaks the chosen proposal into issues (Linear or local `.md`)
4. **Implement** — works through each issue, writing code
5. **Review** — reviews all changes for bugs, security, and style
6. **Compliance** — runs healthcare compliance checklists against the diff

### Compliance checklists

Checklists live in `templates/compliance/` and are fully customizable:

- **HIPAA** — PHI in logs, encryption, access control, audit trails, minimum necessary
- **SOC2** — input validation, error handling, dependency auditing
- **HITRUST** — session management, credential handling

Each item gets a pass/warn/fail status. Failures block the commit gate (with override + justification).

## Credits

- **RePPIT methodology** — [Mikhail Eric](https://github.com/mikhailejohneric), Stanford University
- **RePPITHealth extension** — [Cara Medical](https://caramedical.com)

## License

Apache 2.0 — see [LICENSE](LICENSE)
