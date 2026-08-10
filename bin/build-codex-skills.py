#!/usr/bin/env python3
"""Generate Codex/AGENTS.md-style skills from the canonical commands/*.md.

Loobster's source of truth is `commands/*.md` (the Claude Code plugin). Codex (and
any agent that reads `.agents/skills/`) discovers skills as `<name>/SKILL.md` with
`name`/`description` frontmatter. This script mirrors each command into
`.agents/skills/<name>/SKILL.md` so the SAME workflow runs in Codex with no drift.

  python3 bin/build-codex-skills.py            # regenerate .agents/skills/**
  python3 bin/build-codex-skills.py --check     # exit 1 if regeneration would change anything (CI)

Path rewrites applied to each body:
  ${CLAUDE_PLUGIN_ROOT}/commands/<x>.md  ->  .agents/skills/<x>/SKILL.md
  ${CLAUDE_PLUGIN_ROOT}/<rest>           ->  <rest>            (repo-root relative)
"""
import sys, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CMD = ROOT / "commands"
REF = ROOT / "reference"          # shared reference docs (not slash commands)
OUT = ROOT / ".agents" / "skills"

# Trigger-oriented descriptions (Codex uses these for implicit invocation).
DESC = {
 "run": "Run the full RePPITS workflow (Research -> Propose -> Plan -> Implement -> Test -> Secure) with risk-tiered approval gates. Use to build or change a feature end-to-end. Not for tiny one-off edits.",
 "loop": "Run a continuous goal-loop: work a prioritized RICE-scored backlog toward a standing goal, cycle after cycle, consuming/emitting signals. Use for ongoing autonomous improvement toward a goal; not for a single discrete task (use run).",
 "resume": "Resume a paused, interrupted, or crashed RePPITS workflow by reconstructing state from tasks. Use when continuing prior workflow work after a break.",
 "signals": "Emit or consume cross-loop signals (observations / frictions / opportunities) in the shared signals/ store. Use to record a finding for other loops or teammates, or to read relevant ones before deciding. PHI must never go in a signal.",
 "team-setup": "Wire a repo for Loobster's team layer in one command: vendor the fleet dashboard workflow + the scripts it runs in CI, scaffold signals/ and plans/loop/, and enable GitHub Pages via gh (refusing on public repos unless explicitly overridden). Use when onboarding a repo to the team features.",
 "verify-frontend": "Verify UI changes by capturing Playwright screenshots and attaching them to the PR (GitHub-native, no third-party hosts). Use when a change touches the frontend.",
 "research-codebase": "Document the existing codebase exactly as it is today (no suggestions, no fixes). Use as the first phase, before proposing changes.",
 "make-proposals": "Generate up to two solution proposals grounded in prior research (with architecture diagrams). Use after research, before planning.",
 "make-plan": "Break the chosen proposal into ordered issues/tasks with dependencies. Use after a proposal is chosen, before implementing.",
 "implement": "Implement a single planned issue, optionally inside a bounded autonomous loop. Use to execute one unit of an approved plan.",
 "review-code": "Review all uncommitted changes (the Test phase) in a SEPARATE verifier — never self-review. Use before securing/committing.",
 "secure": "Run the enabled compliance checklists (any of HIPAA / HITRUST / ISO 27001 / SOC 2) against the diff, separating code-verifiable findings from organizational controls. Always run before committing a sensitive change.",
 "backlog-scoring": "Reference only (do NOT invoke as an action): the RICE scoring convention for the goal-loop backlog. Read by the loop/make-plan skills.",
 "token-discipline": "Reference only (do NOT invoke as an action): token-reduction conventions (subagent isolation, artifact compaction). Applied throughout the other skills.",
}

def rewrite(body: str) -> str:
    body = re.sub(r"\$\{CLAUDE_PLUGIN_ROOT\}/(?:commands|reference)/([a-z0-9-]+)\.md",
                  r".agents/skills/\1/SKILL.md", body)
    body = body.replace("${CLAUDE_PLUGIN_ROOT}/", "")
    return body

def build():
    # Slash commands live in commands/; shared reference docs live in reference/.
    # Both are mirrored into .agents/skills/ for Codex; the reference docs carry a
    # "reference only" description so Codex doesn't invoke them as actions.
    files = [(f, "commands") for f in sorted(CMD.glob("*.md"))]
    files += [(f, "reference") for f in sorted(REF.glob("*.md"))]
    generated = {}
    for f, src in files:
        name = f.stem
        desc = DESC.get(name, f"Loobster command: {name}.")
        body = rewrite(f.read_text(encoding="utf-8")).rstrip() + "\n"
        skill = (
            "---\n"
            f"name: {name}\n"
            f"description: {desc}\n"
            "---\n\n"
            f"<!-- GENERATED from {src}/{name}.md by bin/build-codex-skills.py — do not edit here. -->\n\n"
            f"{body}"
        )
        generated[name] = skill
    return generated

def main():
    check = "--check" in sys.argv
    generated = build()
    changed = []
    for name, content in generated.items():
        dest = OUT / name / "SKILL.md"
        old = dest.read_text(encoding="utf-8") if dest.exists() else None
        if old != content:
            changed.append(name)
            if not check:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
    if check:
        if changed:
            print("OUT OF SYNC (run bin/build-codex-skills.py):", ", ".join(changed)); sys.exit(1)
        print("codex skills in sync"); return
    print(f"wrote {len(generated)} skills to .agents/skills/ ({len(changed)} changed)")

if __name__ == "__main__":
    main()
