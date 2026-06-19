Run healthcare security checks (HIPAA, SOC2, HITRUST) against all uncommitted changes.

## What this does

- Gathers all uncommitted changes (staged + unstaged)
- Runs each enabled security framework checklist against the diff
- Produces a pass/warn/fail report for **code-verifiable** items
- Surfaces **organizational `[org]` items** separately as "NOT VERIFIED — requires manual/periodic review"
- Optionally posts findings to the relevant issue tracker

## Steps

1. Collect the diff:
   - `git diff`
   - `git diff --cached`
   - `git diff HEAD`
2. If an issue ID is provided or can be inferred from the branch name, read it for context.
3. Read the compliance checklist files for each enabled framework:
   - `${CLAUDE_PLUGIN_ROOT}/compliance/hipaa-checklist.md` (if HIPAA is enabled)
   - `${CLAUDE_PLUGIN_ROOT}/compliance/soc2-checklist.md` (if SOC2 is enabled)
   - `${CLAUDE_PLUGIN_ROOT}/compliance/hitrust-checklist.md` (if HITRUST is enabled)
   If a workspace override exists at `.claude/compliance/<framework>-checklist.md` in the user's repo, prefer that. If neither exists, fall back to the built-in checks below.
4. Run each security checklist against the diff.
   - **Token discipline (see `${CLAUDE_PLUGIN_ROOT}/commands/token-discipline.md`):** when the diff is large or several frameworks are enabled, delegate each framework's checklist evaluation to its own `Agent` subagent and collect only the per-item PASS/WARN/FAIL verdicts. The main thread assembles the report from those verdicts. Never let a subagent's raw file reads back into the main context — only the verdicts.
5. **For items marked `[org]`**: Do NOT auto-pass these. Instead, check if the diff touches files relevant to that control (e.g., CDK/infrastructure changes for physical safeguards, CI/CD changes for change management). If the diff is relevant, evaluate what you can. If not, mark as `SKIPPED` with a note that it requires periodic organizational review.
6. For each code-verifiable item, assign a status:
   - **PASS** — requirement met
   - **WARN** — potential concern, needs human review
   - **FAIL** — clear violation found
   - **SKIPPED** — cannot be verified from code diff (organizational/physical control)
7. Present the report using the output template below.
8. If Linear MCP tools are available and an issue was identified, post the security report as a comment.
9. If Claude Code Tasks track this work (`TaskList`), record the result: any task with an unresolved **FAIL** stays `in_progress` (a FAIL blocks completion); mark tasks `completed` only when no FAIL remains. This keeps `/resume-reppit` and the Phase 6 convergence loop accurate across sessions.

### Built-in HIPAA Checks (fallback)

- No PHI (names, DOB, SSN, emails, phone numbers) in logs, comments, error messages, or string literals
- Data at rest encryption (no plaintext storage of sensitive fields)
- Data in transit (HTTPS/TLS for all external calls)
- Access control (authentication checks, proper authorization)
- Audit trail (data access/modification is logged)
- Minimum necessary (only required data fields are queried/returned)
- Soft delete only (no hard deletes of patient/health data)

### Built-in SOC2 Checks (fallback)

- Input validation on all API boundaries
- Error handling does not leak internal details to clients
- Dependencies are pinned (no floating versions)
- No secrets or credentials in code
- Change management (PR review, automated deployment)

### Built-in HITRUST Checks (fallback)

- Session management (proper token handling, expiry)
- Credential handling (no plaintext passwords, proper hashing)
- Cross-tenant data access prevention
- Encryption (strong algorithms, no weak crypto)

## Output template

```
## Security Review

Summary: <1-2 sentences>

### HIPAA
| Status | Check | Detail |
|--------|-------|--------|
| PASS/WARN/FAIL | <check name> | <explanation> |

### SOC2
| Status | Check | Detail |
|--------|-------|--------|
| PASS/WARN/FAIL | <check name> | <explanation> |

### HITRUST
| Status | Check | Detail |
|--------|-------|--------|
| PASS/WARN/FAIL | <check name> | <explanation> |

### Organizational Controls (not verifiable from code)
| Framework | Control | Last Verified | Action Required |
|-----------|---------|---------------|-----------------|
| HIPAA §164.310 | Physical safeguards | See periodic audit | Quarterly review |
| SOC2 CC1.2 | Board oversight | See periodic audit | Quarterly review |
| ... | ... | ... | ... |

Items skipped: <count> (see periodic audit schedule in `${CLAUDE_PLUGIN_ROOT}/compliance/org-controls-audit.md`)

Blocking issues: <count>
```

## Notes

- FAIL items should block any commit/push — flag clearly.
- WARN items need human judgment — present but don't block.
- SKIPPED items are organizational controls — they do NOT block but must be tracked via periodic audit.
- This command can be run standalone or as part of the full `/reppit` flow.
- If this diff touches infrastructure (CDK, K8s, CI/CD), evaluate relevant `[org]` items against the infrastructure changes rather than skipping them.
