# Product

## Register

product

## Users

Software engineers and eng leads running AI coding agents (Claude Code / Codex) on shared codebases — often in regulated (healthcare) orgs. They open the fleet dashboard between tasks or from a phone with one question: *what are the loops doing, is anything stuck, what's queued?* Sessions are seconds-long glances plus the occasional control action (pause a loop, file a task), not extended work. Terminal-native people; GitHub is their home turf.

## Product Purpose

Loobster turns AI-assisted development into a gated, verifiable loop. The fleet dashboard is the team's single pane over every loop on every branch — status, backlog, signals — served from GitHub Pages with git as the only data plane (no servers, every action an audit-logged commit). Success: a teammate assesses fleet health in under ten seconds and can pause / stop / file work in one motion from any device, trusting that what they see is real — and that staleness is *visible*.

## Brand Personality

Terminal-native, honest, quietly playful. The voice states facts plainly ("a stale page looks stale instead of confidently wrong") and never oversells. The one flash of personality is the red lobster. Calm competence over dashboard theater.

## Anti-references

- SaaS analytics dashboards (Datadog/Amplitude-style): gradient heroes, KPI stat tiles, chart junk. This is a control surface, not a stats showcase.
- Jira: dense chrome, modal mazes, configuration sprawl. The board is one glanceable page.
- "AI product" styling: purple gradients, sparkles, glassmorphism.

## Design Principles

- **Truth over polish.** Ages compute client-side; staleness, emptiness, and errors render honestly. Never show confidence the data doesn't have.
- **Every action is a commit.** Controls map 1:1 to audit-logged git writes; the UI makes that legible (say what will be committed, where).
- **Glance-first hierarchy.** Status → what needs attention → detail, in that order, readable on a phone at arm's length.
- **Zero dependencies, zero servers.** One self-contained HTML file; every byte earns its place.
- **Quiet until it matters.** Color encodes state (active / paused / parked / alert), never decoration.

## Accessibility & Inclusion

WCAG 2.1 AA: ≥4.5:1 body-text contrast in both themes, full keyboard operability for every control, visible focus states, `prefers-reduced-motion` honored, and state always conveyed by text + color, never color alone.
