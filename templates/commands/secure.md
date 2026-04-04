Run healthcare security checks (HIPAA, SOC2, HITRUST) against all uncommitted changes.

## What this does
- Gathers all uncommitted changes (staged + unstaged)
- Runs each enabled security framework checklist against the diff
- Produces a pass/warn/fail report per checklist item
- Optionally posts findings to the relevant issue tracker

## Steps
1. Collect the diff:
   - `git diff`
   - `git diff --cached`
   - `git diff HEAD`
2. If an issue ID is provided or can be inferred from the branch name, read it for context.
3. Read the compliance checklist files for each enabled framework:
   - `.claude/compliance/hipaa-checklist.md` (if HIPAA is enabled)
   - `.claude/compliance/soc2-checklist.md` (if SOC2 is enabled)
   - `.claude/compliance/hitrust-checklist.md` (if HITRUST is enabled)
   If the files don't exist, use the built-in checks below as defaults.
4. Run each security checklist against the diff:

### HIPAA Checklist
- No PHI (names, DOB, SSN, emails, phone numbers) in logs, comments, error messages, or string literals
- Data at rest encryption (no plaintext storage of sensitive fields)
- Data in transit (HTTPS/TLS for all external calls)
- Access control (authentication checks, proper authorization)
- Audit trail (data access/modification is logged)
- Minimum necessary (only required data fields are queried/returned)
- Soft delete only (no hard deletes of patient/health data)

### SOC2 Checklist
- Input validation on all API boundaries
- Error handling does not leak internal details to clients
- Dependencies are pinned (no floating versions)
- No secrets or credentials in code

### HITRUST Checklist
- Session management (proper token handling, expiry)
- Credential handling (no plaintext passwords, proper hashing)
- Cross-tenant data access prevention

5. For each item, assign a status:
   - PASS — requirement met
   - WARN — potential concern, needs human review
   - FAIL — clear violation found
6. Present the report.
7. If Linear MCP tools are available and an issue was identified, post the security report as a comment.

## Output template
```
## Security Review (RePPITS)

Summary: <1-2 sentences>

### HIPAA
| Status | Check | Detail |
|--------|-------|--------|
| PASS/WARN/FAIL | <check name> | <explanation> |

### SOC2
...

### HITRUST
...

Blocking issues: <count>
```

## Notes
- FAIL items should block any commit/push — flag clearly.
- WARN items need human judgment — present but don't block.
- This command can be run standalone or as part of the full `/reppit` flow.
