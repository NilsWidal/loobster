Generate two solution proposals grounded in existing research and a feature or project request.

## Behavior
- Require a research document produced by `/research-codebase` (either a local file path or a Linear document).
- Produce two distinct solution approaches, each tied back to the research findings.
- Highlight trade-offs, impacted systems, validation steps, and open questions per proposal.

## Steps
1. Intake
   - Capture the user's request. If a Linear issue or project is referenced and Linear MCP tools are available, read it.
   - Read the research document (local file or Linear document).
2. Parse research
   - Extract constraints, relevant modules, dependencies, data flows, and prior decisions.
3. Synthesize solution space
   - Derive candidate approaches grounded in the research findings.
   - For each approach, note primary changes, affected code paths, required migrations/config updates, and rollout considerations.
   - Keep the list to two distinct proposals, ordered from most to least aligned with constraints.
4. Validation planning
   - Identify verification strategies (tests, experiments, observability) necessary to prove each approach.
   - Surface critical unknowns or prerequisite research.
5. Save proposals:
   - If Linear MCP tools are available, save as a Linear document.
   - Also save locally for reference.
6. Present the proposals to the user for a decision.

## Output template
```
## Solution Proposals

Context:
- Request: <short restatement of the ask>
- Research Source: <document or filename and key sections used>

Proposal 1 — <title>
- Overview: <2-3 sentences>
- Key Changes: <components/modules>
- Trade-offs: <risks vs benefits>
- Validation: <tests/experiments/metrics>
- Open Questions: <gaps or follow-ups>

Proposal 2 — <title>
...
```

## Notes
- Reference code and sections using `path/to/file.py:lines` when citing specifics.
- When the research does not directly address the request, call out the gaps and suggest additional research before proposing solutions.
- Stay concise; favor clarity over exhaustive detail.
