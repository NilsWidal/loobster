# SOC2 Trust Service Criteria Checklist

Review each item against the code diff. For each, assign: **PASS**, **WARN**, or **FAIL**.
Items marked *[org]* may not be directly visible in the diff — verify the organizational control exists.
Control IDs reference the 2017 Trust Service Criteria (TSC).

---

## CC1 — Control Environment

### CC1.1 COSO Principle 1: Integrity & Ethical Values
- [ ] *[org]* Code of conduct is not undermined (no backdoors, no deliberately misleading behavior)
- [ ] No "magic" admin endpoints that bypass normal access controls

### CC1.2 COSO Principle 2: Board Oversight
- [ ] *[org]* Security-relevant changes (auth, encryption, infra) have appropriate reviewer approval

### CC1.3 COSO Principle 3: Management Structure
- [ ] *[org]* Changes to CI/CD pipelines, deployment scripts, or infrastructure are reviewed by authorized personnel

---

## CC2 — Communication & Information

### CC2.1 Internal Communication
- [ ] Security-relevant code changes include comments explaining the "why" (not just the "what")
- [ ] Breaking changes to APIs or data schemas are documented in changelogs or migration guides

### CC2.2 External Communication
- [ ] User-facing error messages do not expose system internals
- [ ] Public API changes maintain backward compatibility or include deprecation notices

---

## CC3 — Risk Assessment

### CC3.1 Risk Identification
- [ ] New features that handle sensitive data include threat model considerations (even as comments)
- [ ] Third-party integrations are evaluated for data flow risk (what data goes where)

### CC3.2 Fraud Risk
- [ ] Financial operations (billing, credits, subscriptions) validate amounts server-side
- [ ] No client-side-only price or quantity validation that could be bypassed

### CC3.3 Change-Related Risk
- [ ] Database migrations have rollback plans or are idempotent (`IF NOT EXISTS` guards)
- [ ] Feature flags or gradual rollouts are used for high-risk changes (where appropriate)

---

## CC4 — Monitoring Activities

### CC4.1 Ongoing Monitoring
- [ ] Health check endpoints are not removed or degraded
- [ ] Metrics, alerts, and dashboards are preserved (no silent removal of monitoring)
- [ ] Error tracking (Sentry, etc.) is maintained in all error paths

### CC4.2 Deficiency Communication
- [ ] TODO/FIXME/HACK comments in security-critical code are flagged, not ignored
- [ ] Known deficiencies are tracked (issue trackers, not just code comments)

---

## CC5 — Control Activities

### CC5.1 Risk-Mitigating Controls
- [ ] Security controls (rate limiting, CORS, CSP, CSRF protection) are not weakened
- [ ] Defense-in-depth: multiple layers of validation exist (client + server, not just one)

### CC5.2 Technology Controls
- [ ] Automated tests cover security-critical paths (auth, authorization, data access)
- [ ] CI/CD pipelines include security scanning and are not bypassed (`--no-verify` is not used)

---

## CC6 — Logical & Physical Access Controls

### CC6.1 Logical Access — Infrastructure
- [ ] *[org]* Infrastructure changes (CDK, Terraform, K8s manifests) maintain least-privilege IAM policies
- [ ] No wildcard (`*`) permissions added to IAM roles or security groups
- [ ] Management ports (SSH, RDP, database) are not exposed to public internet

### CC6.2 Logical Access — Software
- [ ] Authentication required on all new endpoints
- [ ] Authorization checks enforce role-based access (RBAC) — not hardcoded role strings
- [ ] Multi-factor authentication is not weakened or bypassed
- [ ] Session tokens have appropriate expiry and are invalidated on logout

### CC6.3 Logical Access — Least Privilege
- [ ] API scopes and permissions follow least privilege — endpoints only grant what's needed
- [ ] Service accounts use minimal required permissions
- [ ] Admin/superadmin functionality is restricted and logged

### CC6.4 Physical Access
- [ ] *[org]* Cloud provider physical security controls are inherited (AWS SOC2 report)

### CC6.5 Logical Access — Removal
- [ ] Account deactivation triggers session invalidation
- [ ] Removed users/roles lose access immediately (no stale session persistence)

### CC6.6 Threat Detection
- [ ] Failed authentication attempts are logged with metadata (IP, user agent, timestamp)
- [ ] Anomalous access patterns trigger alerts (rate limits, geo-blocking, etc.)

### CC6.7 Identity Management
- [ ] Tenant isolation: all queries scoped to authenticated tenant (no cross-tenant data leakage)
- [ ] Background jobs and scheduled tasks enforce tenant context
- [ ] API keys and tokens are scoped to specific tenants/users

### CC6.8 Code Execution Safety
- [ ] No `eval()`, `new Function()`, or dynamic code execution from user input
- [ ] `dangerouslySetInnerHTML` is only used with sanitized content (DOMPurify or equivalent)
- [ ] No server-side template injection vectors
- [ ] No command injection via unsanitized input in shell commands (`child_process`, `exec`, etc.)
- [ ] No SQL injection — parameterized queries or ORM used for all database access
- [ ] No path traversal — file paths from user input are validated/sandboxed

---

## CC7 — System Operations

### CC7.1 Infrastructure Monitoring
- [ ] System health endpoints exist and function correctly
- [ ] Resource utilization (CPU, memory, disk, connections) is monitored
- [ ] Alerting thresholds are not raised to suppress legitimate warnings

### CC7.2 Error Handling
- [ ] Error responses do not leak stack traces, internal paths, or implementation details
- [ ] Unexpected errors return generic messages to clients
- [ ] Errors are logged server-side with sufficient context for debugging
- [ ] No empty catch blocks — all exceptions are logged or rethrown
- [ ] Error classification exists (retryable vs. fatal) for queue-based processing

### CC7.3 Logging & Audit Trail
- [ ] All API routes have structured error logging
- [ ] Security events (login, logout, permission changes, data access) are logged
- [ ] Logs include correlation IDs for request tracing
- [ ] Log levels are appropriate (no DEBUG in production, no suppressed ERROR)

### CC7.4 Incident Management
- [ ] Error paths that indicate security incidents trigger appropriate alerts
- [ ] Incident response runbooks are referenced (not removed) in infrastructure changes
- [ ] Dead letter queues (DLQ) have monitoring and alerting

### CC7.5 Disaster Recovery
- [ ] Database changes include migration rollback plans
- [ ] Backup configurations are not weakened
- [ ] Failover mechanisms are preserved

---

## CC8 — Change Management

### CC8.1 Change Authorization
- [ ] *[org]* Changes go through pull request review before merge
- [ ] Infrastructure changes have `cdk diff` or equivalent preview before deploy
- [ ] Database migrations are reviewed separately from application code

### CC8.2 Change Testing
- [ ] New features have automated tests
- [ ] Breaking changes have migration tests
- [ ] Security-critical changes have specific test coverage

### CC8.3 Change Deployment
- [ ] Deployment process is automated (no manual production changes)
- [ ] Rollback procedures exist for failed deployments
- [ ] Feature flags or canary deployments for high-risk changes

---

## CC9 — Risk Mitigation

### CC9.1 Vendor Risk
- [ ] New dependencies are from trusted sources (no typosquatting risk)
- [ ] Dependencies are pinned to exact versions (no floating `^` or `~` in production)
- [ ] No known critical vulnerabilities in added/updated dependencies (`npm audit`)
- [ ] Third-party scripts are loaded with integrity hashes (SRI) where applicable

### CC9.2 Business Disruption Risk
- [ ] New external service calls have timeout and retry logic
- [ ] Circuit breaker patterns for unreliable external services
- [ ] Graceful degradation when optional services are unavailable

---

## A1 — Availability

### A1.1 Capacity Planning
- [ ] Database queries have reasonable limits to prevent resource exhaustion
- [ ] No unbounded loops, memory allocations, or result sets based on user input
- [ ] Pagination is enforced on list/search endpoints

### A1.2 Environmental Protections
- [ ] Rate limiting is preserved on public-facing endpoints
- [ ] DDoS protections (WAF, CloudFront, etc.) are not weakened
- [ ] Resource quotas exist for tenant-scoped operations

### A1.3 Recovery
- [ ] Backup and restore procedures are not impacted by the change
- [ ] Data replication configurations are maintained
- [ ] Recovery Time Objective (RTO) and Recovery Point Objective (RPO) are not degraded

---

## C1 — Confidentiality

### C1.1 Confidential Information Identification
- [ ] Sensitive data (PHI, PII, credentials, financial data) is classified and handled appropriately
- [ ] No sensitive data in client-side code, logs, or analytics

### C1.2 Confidential Information Disposal
- [ ] Temporary storage of confidential data is cleaned up on schedule
- [ ] Export/download features enforce authorization and audit logging

---

## PI1 — Processing Integrity

### PI1.1 Accuracy & Completeness
- [ ] Data transformations are lossless (no silent truncation or rounding)
- [ ] Input validation ensures data integrity at system boundaries
- [ ] Race conditions are handled (optimistic locking, transactions, idempotency keys)

### PI1.2 Error Detection
- [ ] Data validation errors are surfaced to users with actionable messages
- [ ] Webhook/event processing has deduplication or idempotency

---

## P1 — Privacy (applicable for PHI/PII)

### P1.1 Notice & Consent
- [ ] Data collection points have appropriate privacy notices
- [ ] Consent is obtained before collecting/processing personal data
- [ ] Consent records are stored and auditable

### P1.2 Choice & Use Limitation
- [ ] Personal data is used only for stated purposes
- [ ] Opt-out mechanisms are functional and respected

### P1.3 Access & Correction
- [ ] Users can access their own data via API/UI
- [ ] Data correction/update mechanisms exist

### P1.4 Disclosure & Data Minimization
- [ ] Third-party data sharing requires explicit authorization
- [ ] API responses return only necessary fields (no over-fetching)

### P1.5 Data Quality
- [ ] Input validation ensures data quality at ingestion
- [ ] Data normalization is applied consistently (dates, phone numbers, etc.)

### P1.6 Security for Privacy
- [ ] All privacy-relevant controls from CC6/CC7 above apply
- [ ] Data subject requests (access, deletion) are implementable

---

## Secrets & Credentials

- [ ] No secrets, API keys, tokens, or passwords in source code
- [ ] No credentials in configuration files committed to version control
- [ ] Environment variables or secret managers used for all sensitive config
- [ ] `.env` files are in `.gitignore`
- [ ] No credentials in Docker images or build artifacts

---

## Input Validation & Injection Prevention

- [ ] All API endpoints validate input (schema validation with zod/yup/joi)
- [ ] User-supplied data is sanitized before use in queries, templates, or commands
- [ ] File uploads are validated (type, size, content) and stored outside webroot
- [ ] No SSRF vectors — server-side URL fetching validates/restricts target URLs
- [ ] GraphQL endpoints have depth/complexity limits

---

## Output markers

For each item above, emit a structured marker:

```
<!-- SECURE_ITEM:pass|warn|fail:CC#.#:Check Name:Detail about the finding -->
```
