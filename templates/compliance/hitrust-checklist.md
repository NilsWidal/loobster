# HITRUST CSF Security Checklist

Review each item against the code diff. For each, assign: PASS, WARN, or FAIL.

## Session Management
- [ ] Sessions/tokens have appropriate expiry times
- [ ] Token refresh logic is implemented correctly (no indefinite sessions)
- [ ] Session invalidation on logout or password change
- [ ] Tokens are stored securely (httpOnly cookies, not localStorage for sensitive tokens)

## Credential Handling
- [ ] Passwords are hashed with a strong algorithm (bcrypt, scrypt, argon2) — never stored in plaintext
- [ ] Password reset flows do not reveal whether an account exists
- [ ] Multi-factor authentication flows are correctly implemented (if applicable)

## Cross-Tenant Isolation
- [ ] Database queries are scoped to the authenticated tenant
- [ ] No shared state between tenants (caches, queues, file storage)
- [ ] Tenant identifiers are validated server-side, never trusted from client input alone
- [ ] Background jobs and scheduled tasks enforce tenant context

## Data Integrity
- [ ] Critical operations use database transactions
- [ ] Concurrent access to shared resources is handled (optimistic locking, etc.)
- [ ] Data migrations are reversible or have a rollback plan

## Output markers
For each item above, emit a structured marker:
```
<!-- SECURE_ITEM:pass|warn|fail:Check Name:Detail about the finding -->
```
