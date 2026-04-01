# RePPIT Health

AI-powered secure development workflow for healthcare software.

**RePPIT Health** implements the **RePPITS** methodology — **R**esearch, **P**ropose, **P**lan, **I**mplement, **T**est, **S**ecure — extending the [RePPIT framework](https://themodernsoftware.dev) by [Mihail Eric](https://github.com/mihail911) (Head of AI, creator of Stanford's first AI software engineering course) with HIPAA, SOC2, and HITRUST security gates for healthcare and healthtech teams.

## What it does

A VS Code / Cursor sidebar extension that guides you through a complete development workflow powered by Claude Code:

```
Research --> Propose --> Plan --> Implement --> Test --> Secure --> Done
   ^            ^          ^         ^           ^         |
   | refine     | refine   | refine  | fix loop  | fix     |
   └────┘       └────┘     └────┘    └────┘      └──┘      |
                                          ^                 |
                                          └── fix & test ───┘
```

Each phase has a **gate** — the workflow pauses, plays a sound, and waits for your approval before advancing. You can refine any phase as many times as needed.

## Installation

### Prerequisites

- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/overview)** — installed and authenticated (`claude` must be on your PATH)
- **Node.js 18+**
- **VS Code ^1.85** or **Cursor**

### Install from Marketplace

- **VS Code**: Search "RePPIT Health" in the Extensions view, or run `ext install caramedical.reppit-health`
- **Cursor / Open VSX**: Available on the [Open VSX Registry](https://open-vsx.org/)

### Install from .vsix

Download the latest `.vsix` from [GitHub Releases](https://github.com/carainc/reppit-health/releases), then:

```bash
code --install-extension reppit-health-*.vsix
# or for Cursor:
cursor --install-extension reppit-health-*.vsix
```

### Build from source

```bash
git clone https://github.com/carainc/reppit-health.git
cd reppit-health
npm ci
npm run build
npm run package
code --install-extension reppit-health-*.vsix
```

## Quick start

1. Open a project in VS Code / Cursor
2. Click the **RePPIT Health** icon in the activity bar (sidebar)
3. Type a feature description (e.g., "Add patient intake form") or a Linear issue ID (e.g., `CAR-123`)
4. Press **Start** — the workflow runs Research → Propose → Plan, then pauses for your review
5. Approve the plan (or refine it), and the extension continues through Implement → Test → Secure

The extension auto-scaffolds `.claude/commands/` templates into your workspace on first run. You can customize these per project.

## Features

- **Visual sidebar** — phase stepper, gate buttons, real-time Claude output log
- **Security gates** — HIPAA, SOC2, HITRUST checklists run against your diff before commit
- **`/secure` command** — run security checks standalone, anytime
- **Linear integration** (optional) — creates issues, documents, and comments in Linear. Falls back to local `.md` files if Linear MCP is not configured
- **Sound notifications** — plays a sound when your input is needed
- **CLI detection** — warns on activation if Claude Code CLI is not found, with install link
- **Works in VS Code and Cursor**

## Configuration

All settings are under `reppithealth.*` in VS Code settings.

| Setting | Default | Description |
|---------|---------|-------------|
| `reppithealth.notifications.sound` | `true` | Play sound at gates |
| `reppithealth.notifications.system` | `true` | Show system notifications |
| `reppithealth.compliance.hipaa` | `true` | Enable HIPAA security checks |
| `reppithealth.compliance.soc2` | `false` | Enable SOC2 security checks |
| `reppithealth.compliance.hitrust` | `false` | Enable HITRUST security checks |
| `reppithealth.claudePath` | `claude` | Path to Claude CLI binary |
| `reppithealth.autoApprove` | `false` | Skip Claude tool approval prompts (see below) |
| `reppithealth.claudeTrace` | `false` | Show verbose Claude CLI debug output |
| `reppithealth.taskMode` | `stream` | Task tracking mode (`stream` or `poll`) |

### About `autoApprove`

When enabled, the extension passes `--dangerously-skip-permissions` to the Claude CLI, meaning Claude can read/write files and run commands without prompting for each action. This makes the workflow faster but gives Claude full access to your workspace. Only enable this if you trust the workflow running in your project.

## How it works

The extension spawns the Claude CLI as a child process and communicates via structured markers in the stream-json output. Your `.claude/commands/*.md` files define the behavior of each phase — you can customize them per project.

### Phases

1. **Research** — Claude explores your codebase and documents findings
2. **Propose** — generates 2 solution proposals with trade-offs
3. **Plan** — breaks the chosen proposal into issues (Linear or local `.md`)
4. **Implement** — works through each issue, writing code
5. **Test** — reviews and tests all changes for bugs, correctness, and style
6. **Secure** — runs enabled healthcare security checklists against the diff. If issues are found, loops back to Implement → Test → Secure until clean

### Security checklists

Checklists live in `templates/compliance/` and are scaffolded to `.claude/compliance/` in your workspace. They are fully customizable:

- **HIPAA** — PHI in logs, encryption, access control, audit trails, minimum necessary
- **SOC2** — input validation, error handling, dependency auditing, secrets
- **HITRUST** — session management, credential handling, tenant isolation

Each item gets a pass/warn/fail status. Only the frameworks you enable in settings are checked.

### Standalone `/secure` command

You can also run the Secure phase independently via the `/secure` Claude Code command — useful for checking existing code without running the full workflow.

## Credits

- **RePPIT methodology** — [Mihail Eric](https://github.com/mihail911), Head of AI, creator of [Stanford's first AI software engineering course](https://themodernsoftware.dev)
- **RePPIT Health extension** — [Cara](https://caramedical.com)

## License

Apache 2.0 — see [LICENSE](LICENSE)
