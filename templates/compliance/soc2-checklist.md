# SOC2 Security Checklist

Review each item against the code diff. For each, assign: PASS, WARN, or FAIL.

## Input Validation
- [ ] All API endpoints validate input (schema validation, type checking)
- [ ] User-supplied data is sanitized before use in queries, templates, or commands
- [ ] File uploads are validated (type, size, content)

## Error Handling
- [ ] Error responses do not leak stack traces, internal paths, or implementation details
- [ ] Unexpected errors return generic messages to clients
- [ ] Errors are logged server-side with sufficient context for debugging

## Dependencies
- [ ] New dependencies are pinned to exact versions (no floating `^` or `~`)
- [ ] No known critical vulnerabilities in added/updated dependencies
- [ ] Dependencies are from trusted sources (no typosquatting risk)

## Secrets & Credentials
- [ ] No secrets, API keys, tokens, or passwords in source code
- [ ] No credentials in configuration files committed to version control
- [ ] Environment variables or secret managers used for all sensitive config

## Availability & Resilience
- [ ] New external service calls have timeout and retry logic
- [ ] Database queries have reasonable limits to prevent resource exhaustion
- [ ] No unbounded loops or memory allocations based on user input

## Output markers
For each item above, emit a structured marker:
```
<!-- SECURE_ITEM:pass|warn|fail:Check Name:Detail about the finding -->
```
