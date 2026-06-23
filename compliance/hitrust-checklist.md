# HITRUST CSF v11 Security Checklist

Review each item against the code diff. For each, assign: **PASS**, **WARN**, **FAIL**, or **SKIPPED** (for [org] or physical controls not verifiable from the diff).
Items marked *[org]* may not be directly visible in the diff — verify the organizational control exists.
Control IDs reference the HITRUST CSF v11 control categories.

---

## 00 — Information Security Management Program

### 00.a Policy & Program
- [ ] *[org]* Security policies are referenced in infrastructure/deployment changes
- [ ] Compliance scanning in CI/CD is not disabled or bypassed
- [ ] Security-relevant decisions are documented (comments, ADRs, or tickets)

---

## 01 — Access Control

### 01.a Access Control Policy
- [ ] All new endpoints enforce authentication
- [ ] Authorization model is role-based (RBAC) with configurable permissions — not hardcoded role strings
- [ ] API scopes follow least privilege — endpoints only grant what's needed
- [ ] Admin/superadmin functionality is restricted, logged, and separated from normal user flows

### 01.b User Registration & Deactivation
- [ ] Account creation enforces email verification or identity proofing
- [ ] Account deactivation immediately invalidates all active sessions and tokens
- [ ] Orphaned data (sessions, tokens, API keys) is cleaned up on account removal

### 01.c Privilege Management
- [ ] Privilege escalation requires explicit authorization (no self-service role elevation)
- [ ] Admin actions are audit-logged with actor identity
- [ ] Service accounts use minimal required permissions
- [ ] No wildcard (`*`) permissions in IAM policies or RBAC configurations

### 01.d User Authentication
- [ ] Multi-factor authentication is enforced for administrative access
- [ ] MFA flows are not weakened or bypassed in the change
- [ ] Password complexity requirements meet policy (min 12 chars, mixed types)
- [ ] Failed authentication attempts are logged with metadata (IP, user agent, timestamp)
- [ ] Account lockout after repeated failures is implemented

### 01.e Password Management
- [ ] Passwords are hashed with a strong algorithm (bcrypt, scrypt, argon2) — never stored in plaintext
- [ ] Password reset flows do not reveal whether an account exists
- [ ] Password history is enforced (no reuse of last N passwords)
- [ ] No default or shared passwords in code or configuration

### 01.j Network Access Control
- [ ] *[org]* Network segmentation: databases and internal services are not publicly accessible
- [ ] VPC/security group changes maintain private subnet placement for data stores
- [ ] Management interfaces (SSH, database consoles) are restricted to VPN/bastion access

### 01.n Segregation in Networks
- [ ] Production, staging, and development environments use separate credentials and data
- [ ] No cross-environment data leakage (dev endpoints pointing to prod databases)

### 01.v Session Management
- [ ] Sessions/tokens have appropriate expiry times (max 8h active, 30min idle)
- [ ] Token refresh logic is implemented correctly (no indefinite sessions)
- [ ] Session invalidation on logout or password change
- [ ] Tokens are stored securely (httpOnly cookies, not localStorage for sensitive tokens)
- [ ] Concurrent session limits are enforced (if policy requires)
- [ ] Session fixation is prevented (new session ID after authentication)

### 01.w Secure Login
- [ ] Login pages are served over HTTPS only
- [ ] Login responses do not differ between valid/invalid usernames (timing-safe)
- [ ] CAPTCHA or rate limiting on login endpoints to prevent brute force

---

## 02 — Human Resources Security

### 02.a Roles & Responsibilities
- [ ] *[org]* Access control changes are reviewed by security-aware personnel

### 02.e Information Security Awareness
- [ ] *[org]* Security-relevant code includes inline comments explaining the control purpose

---

## 03 — Risk Management

### 03.a Risk Assessment
- [ ] New features that handle sensitive data include threat considerations
- [ ] Third-party integrations are evaluated for data flow risk
- [ ] Infrastructure changes reference risk assessment

### 03.b Risk Treatment
- [ ] Identified risks have documented mitigations (not just accepted without comment)
- [ ] Risk acceptance is explicit, not implicit (no silent ignoring of known issues)

---

## 04 — Security Policy

### 04.a Information Security Policy
- [ ] *[org]* Changes to security configurations reference the applicable security policy
- [ ] No changes that contradict documented security policies without formal exception

---

## 05 — Organization of Information Security

### 05.a Internal Organization
- [ ] *[org]* Security-critical changes (auth, crypto, infra) have appropriate reviewer approval
- [ ] Separation of duties: deployment and code review are by different individuals

### 05.i Third-Party Service Delivery
- [ ] New third-party integrations have documented security evaluation
- [ ] Vendor SLAs/uptime commitments are considered for critical-path integrations
- [ ] *[org]* BAAs exist for third parties handling PHI

---

## 06 — Compliance

### 06.a Legal & Regulatory Requirements
- [ ] *[org]* Changes comply with applicable regulations (HIPAA, state privacy laws)
- [ ] Data residency requirements are maintained (data stays in approved regions)

### 06.c Data Protection
- [ ] PHI/PII is encrypted at rest (AES-256 or equivalent)
- [ ] PHI/PII is encrypted in transit (TLS 1.2+)
- [ ] Encryption keys are managed via KMS/Secrets Manager — not hardcoded

### 06.d Cryptographic Controls
- [ ] No weak cryptographic algorithms (MD5, SHA-1 for integrity; DES, RC4 for encryption)
- [ ] Key lengths meet minimum requirements (RSA 2048+, AES 256, ECDSA P-256+)
- [ ] Cryptographic operations use well-maintained libraries (not custom implementations)
- [ ] Certificate validation is not disabled (`rejectUnauthorized: false`, etc.)

### 06.e Prevention of Misuse
- [ ] System resources cannot be abused (unbounded file uploads, compute, memory)
- [ ] Anti-abuse controls (rate limiting, CAPTCHA, fraud detection) are preserved

---

## 07 — Asset Management

### 07.a Asset Inventory
- [ ] *[org]* New infrastructure resources are tagged and inventoried
- [ ] Database schemas changes are tracked in migrations (not ad-hoc)

### 07.b Asset Ownership
- [ ] *[org]* New services/components have designated owners (documented in code or tickets)

### 07.d Information Classification
- [ ] Data classification is consistent (PHI fields marked, non-PHI fields not over-classified)
- [ ] Sensitive data is not mixed with non-sensitive data in shared storage (S3 buckets, tables)

---

## 08 — Physical & Environmental Security

### 08.a Secure Areas
- [ ] *[org]* Cloud provider physical security inherited (AWS SOC2 report)
- [ ] No code changes that bypass cloud provider security controls

### 08.b Equipment Security
- [ ] No hardcoded references to local file paths or physical device assumptions in production code
- [ ] Portable storage/media handling is not relevant to code — skip unless applicable

---

## 09 — Communications & Operations Management

### 09.a Operational Procedures
- [ ] Deployment procedures are documented and automated (CI/CD pipeline)
- [ ] Manual production access is logged and justified
- [ ] Runbooks exist for operational procedures modified by this change

### 09.b Third-Party Service Management
- [ ] Third-party API calls have timeout and retry logic
- [ ] Circuit breakers or fallbacks for unreliable external services
- [ ] Third-party error responses are handled gracefully (not passed through raw)

### 09.e System Planning & Acceptance
- [ ] Load/capacity implications of new features are considered
- [ ] Database queries have reasonable limits to prevent resource exhaustion
- [ ] No unbounded loops, memory allocations, or result sets from user input
- [ ] Pagination enforced on list/search endpoints

### 09.j Information Exchange
- [ ] Data exchanged with external systems is validated at ingestion
- [ ] Webhook payloads are verified (signature validation, source IP checks)
- [ ] Email/SMS content does not contain PHI in plaintext

### 09.l Monitoring & Logging
- [ ] All API routes have structured error logging
- [ ] Security events (login, logout, permission changes, data access) are logged
- [ ] Audit logs include: who, what, when, where (IP/session), outcome
- [ ] Logs do not contain PHI, secrets, or tokens
- [ ] Log retention meets compliance requirements (6+ years for HIPAA)
- [ ] Log integrity: audit logs are append-only or immutable
- [ ] Clock synchronization is maintained (NTP) for log correlation

### 09.m Network Security
- [ ] HTTPS/TLS enforced on all external communications
- [ ] WebSocket connections use WSS, not WS
- [ ] CORS policies are restrictive (not `*` for authenticated endpoints)
- [ ] CSP headers are maintained and not weakened
- [ ] No SSRF vectors — server-side URL fetching validates/restricts targets

### 09.w Secure Transport
- [ ] TLS version not downgraded below 1.2
- [ ] Insecure HTTP redirects to HTTPS (not used alongside HTTPS)
- [ ] API responses include HSTS headers

---

## 10 — Information Systems Acquisition, Development & Maintenance

### 10.a Security Requirements
- [ ] Security requirements are part of the feature design (not bolted on after)
- [ ] Threat modeling for new attack surfaces (endpoints, data flows, integrations)

### 10.b Correct Processing
- [ ] Input validation on all API boundaries (zod/yup/joi schema validation)
- [ ] Output encoding to prevent XSS (React auto-escaping maintained, dangerouslySetInnerHTML sanitized)
- [ ] Data integrity: critical operations use database transactions
- [ ] Concurrent access handled (optimistic locking, idempotency keys)

### 10.c Cryptographic Controls in Systems
- [ ] Secrets and credentials loaded from environment or secret manager
- [ ] No secrets in source code, config files, or Docker images
- [ ] `.env` files in `.gitignore`
- [ ] Key rotation is possible without code changes

### 10.f Technical Vulnerability Management
- [ ] Dependencies pinned to exact versions (no floating `^` or `~`)
- [ ] No known critical vulnerabilities in new dependencies
- [ ] Dependencies from trusted sources (no typosquatting)
- [ ] Dependency audit (`npm audit`) shows no critical/high issues
- [ ] Subresource integrity (SRI) for third-party scripts

### 10.h Change Control
- [ ] *[org]* Changes go through pull request review before merge
- [ ] Infrastructure changes previewed before deploy (`cdk diff`)
- [ ] Database migrations reviewed separately
- [ ] Automated tests for new features and breaking changes
- [ ] Security-critical changes have specific test coverage

### 10.k Change Management
- [ ] TODO/FIXME/HACK comments in production code are tracked and resolved
- [ ] Temporary workarounds have associated tickets for removal
- [ ] No debug code (console.log, debugger statements) in production

---

## 11 — Information Security Incident Management

### 11.a Incident Reporting
- [ ] Error paths that indicate security incidents trigger alerts (Sentry, PagerDuty)
- [ ] Breach detection: unauthorized access patterns trigger immediate notification
- [ ] Incident metadata captured: who, what, when, scope, affected resources

### 11.b Incident Response
- [ ] *[org]* Incident response procedures are not weakened by the change
- [ ] DLQ monitoring and alerting is preserved
- [ ] Error classification exists (retryable vs. fatal vs. poison) for queue processing

---

## 12 — Business Continuity Management

### 12.a Business Continuity Planning
- [ ] Backup configurations are not weakened or removed
- [ ] Database migration changes include rollback plans
- [ ] Failover mechanisms are preserved
- [ ] Recovery Time Objective (RTO) and Recovery Point Objective (RPO) are not degraded

### 12.b Disaster Recovery
- [ ] Critical paths have graceful degradation, not hard failures
- [ ] Multi-region or multi-AZ configurations are maintained
- [ ] Data replication configurations are preserved

---

## 13 — Privacy Practices

### 13.a Privacy Notice
- [ ] Patient-facing applications include Terms of Service, Privacy Policy, and HIPAA Notice
- [ ] Data collection points have appropriate consent mechanisms
- [ ] Privacy preferences are stored and enforced

### 13.b Choice & Consent
- [ ] Consent is obtained before collecting/processing personal data
- [ ] Opt-out mechanisms are functional and respected
- [ ] Consent records are stored and auditable

### 13.d Data Minimization
- [ ] Only necessary data is collected and retained
- [ ] Database queries select only required fields
- [ ] API responses return minimum necessary data
- [ ] Data used for analytics/AI is de-identified or aggregated

### 13.e Access & Correction
- [ ] Data subjects can access their own data
- [ ] Data correction/update mechanisms exist and are logged
- [ ] Data portability is supported (export in standard formats)

### 13.f Data Disposal
- [ ] Patient data uses soft delete only
- [ ] Temporary data is cleaned up on schedule (workspace GC)
- [ ] Data retention policies are enforced programmatically

---

## Cross-Tenant Isolation (Healthcare Multi-Tenancy)

- [ ] Database queries scoped to authenticated tenant — no cross-tenant data leakage
- [ ] No shared state between tenants (caches, queues, file storage paths)
- [ ] Tenant identifiers validated server-side, never trusted from client input alone
- [ ] Background jobs and scheduled tasks enforce tenant context
- [ ] S3 paths include tenant ID in the key prefix
- [ ] Error messages do not leak information about other tenants

---

## Output markers

For each item above, emit a structured marker:

```
<!-- SECURE_ITEM:pass|warn|fail|skip:HITRUST ##.x:Check Name:Detail about the finding -->
```
