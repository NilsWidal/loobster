# Contributing to RePPIT Health

Thanks for your interest in contributing!

## Getting started

1. Fork and clone the repo
2. `npm install`
3. `npm run watch` to start the extension compiler in watch mode
4. Press F5 in VS Code to launch the Extension Development Host

## Project structure

```
src/
  extension.ts          — entry point, registers commands and sidebar
  claude/               — CLI wrapper and output parser
  engine/               — workflow state machine
  sidebar/              — webview provider
  notifications/        — sound and system notifications
  linear/               — Linear MCP detection
  templates/            — scaffold logic
templates/
  commands/             — default .claude/commands/*.md templates
  compliance/           — HIPAA/SOC2/HITRUST checklists
  design_doc_template.md
```

## Development workflow

- `npm run build` — build the extension
- `npm run watch` — rebuild on file changes
- `npm test` — run tests
- `npm run package` — produce a `.vsix` file

## Submitting changes

1. Create a branch from `main`
2. Make your changes with clear commit messages
3. Open a pull request with a description of what changed and why
4. Ensure the build passes

## Code style

- TypeScript, strict mode
- Follow existing patterns in the codebase
- Keep changes focused — one concern per PR

## Customizing templates

The compliance checklists and command templates in `templates/` are designed to be generic. If you have domain-specific checks to add (e.g., FDA, GDPR), consider contributing them as optional checklist files.

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 license.
