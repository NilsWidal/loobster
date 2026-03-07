# RePPIT Health

AI-powered secure development workflow for healthcare software.

**RePPIT Health** implements the **RePPITS** methodology — **R**esearch, **P**ropose, **P**lan, **I**mplement, **T**est, **S**ecure — extending the [RePPIT framework](https://themodernsoftware.dev) by [Mihail Eric](https://github.com/mihail911) (Head of AI, creator of Stanford's first AI software engineering course) with HIPAA, SOC2, and HITRUST security gates for healthcare and healthtech teams.

## What it does

A VS Code / Cursor sidebar extension that guides you through a complete development workflow powered by Claude Code:

```
Research  -->  Propose  -->  Plan  -->  Implement  -->  Test  -->  Secure  -->  Done
    ^              ^            ^           ^             ^           ^
    |  refine      |  refine    |  refine   |  fix loop   |  fix loop |  fix found?
    └──────┘       └──────┘     └──────┘    └─────────┘   └──────┘    |
                                                 ^                     |
                                                 └─── Implement fix ──┘
```

Each phase has a **gate** — the workflow pauses, plays a sound, and waits for your approval before advancing. You can refine any phase as many times as needed.

## Features

- **Visual sidebar** — phase stepper, gate buttons, real-time Claude output log
- **Security gates** — HIPAA, SOC2, HITRUST checklists run against your diff before commit
- **`/secure` command** — run security checks standalone, anytime
- **Linear integration** (optional) — creates issues, documents, and comments in Linear. Falls back to local `.md` files if Linear is not configured
- **Sound notifications** — plays a sound when your input is needed
- **Works in VS Code and Cursor**

## Quick start

1. Install the extension
2. Open command palette: `RePPIT Health: Initialize Project Templates`
3. Open the RePPIT Health sidebar
4. Click **Start Workflow** or run `RePPIT Health: Start Workflow` from the command palette

### Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- Node.js 18+

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `reppits.notifications.sound` | `true` | Play sound at gates |
| `reppits.notifications.system` | `true` | Show system notifications |
| `reppits.security.hipaa` | `true` | Enable HIPAA security checks |
| `reppits.security.soc2` | `false` | Enable SOC2 security checks |
| `reppits.security.hitrust` | `false` | Enable HITRUST security checks |
| `reppits.claudePath` | `claude` | Path to Claude CLI |
| `reppits.autoApprove` | `false` | Skip Claude tool approval prompts |

## How it works

The extension spawns the Claude CLI as a child process and communicates via structured markers. Your `.claude/commands/*.md` files define the behavior of each phase — you can customize them per project.

### Phases

1. **Research** — Claude explores your codebase and documents findings
2. **Propose** — generates 2 solution proposals with trade-offs
3. **Plan** — breaks the chosen proposal into issues (Linear or local `.md`)
4. **Implement** — works through each issue, writing code
5. **Test** — reviews and tests all changes for bugs, correctness, and style
6. **Secure** — runs healthcare security checklists (HIPAA/SOC2/HITRUST) against the diff. If issues are found, loops back to Implement → Test → Secure until clean

### Security checklists

Checklists live in `templates/security/` and are fully customizable:

- **HIPAA** — PHI in logs, encryption, access control, audit trails, minimum necessary
- **SOC2** — input validation, error handling, dependency auditing
- **HITRUST** — session management, credential handling

Each item gets a pass/warn/fail status. Failures block the commit gate (with override + justification).

### Standalone `/secure` command

You can also run the Secure phase independently via the `/secure` Claude Code command — useful for checking existing code without running the full workflow.

## Credits

- **RePPIT methodology** — [Mihail Eric](https://github.com/mihail911), Head of AI, creator of [Stanford's first AI software engineering course](https://themodernsoftware.dev)
- **RePPIT Health extension** — [Cara Medical](https://caramedical.com)

## License

Apache 2.0 — see [LICENSE](LICENSE)
