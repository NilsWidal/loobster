# HIPAA Security Rule Checklist

Review each item against the code diff. For each, assign: **PASS**, **WARN**, or **FAIL**.
Items marked *[org]* may not be directly visible in the diff — verify the organizational control exists.

---

## 1. Administrative Safeguards (§164.308)

### 1.1 Security Management Process (§164.308(a)(1))
- [ ] Risk analysis: new features/endpoints have threat considerations documented or referenced
- [ ] Sanctions policy: code does not bypass security controls without documented exception
- [ ] Information system activity review: log aggregation/monitoring is preserved (not removed or weakened)

### 1.2 Workforce Security (§164.308(a)(3))
- [ ] Authorization/supervision: new admin/elevated-privilege endpoints require role checks
- [ ] Workforce clearance: no hardcoded user IDs or accounts granting bypass access
- [ ] Termination procedures: session invalidation on account deactivation is maintained

### 1.3 Information Access Management (§164.308(a)(4))
- [ ] Access authorization: new data access paths enforce explicit permission grants
- [ ] Access establishment & modification: changes to RBAC/permissions are intentional and reviewed
- [ ] *[org]* Isolating healthcare clearinghouse functions (if applicable)

### 1.4 Security Awareness & Training (§164.308(a)(5))
- [ ] Security reminders: code comments reference relevant compliance rules where non-obvious
- [ ] Protection from malicious software: no disabling of security scanners, linters, or CSP headers
- [ ] Login monitoring: failed authentication attempts are logged with sufficient metadata
- [ ] Password management: no weakening of password complexity or rotation requirements

### 1.5 Security Incident Procedures (§164.308(a)(6))
- [ ] Incident response: error paths that indicate breaches or unauthorized access trigger alerts (Sentry, PagerDuty, etc.)
- [ ] Incident reporting: no suppression of security-relevant log entries or error notifications

### 1.6 Contingency Plan (§164.308(a)(7))
- [ ] Data backup plan: changes do not remove or weaken backup configurations
- [ ] Disaster recovery: database migration changes include rollback strategies
- [ ] Emergency mode operation: critical paths have graceful degradation, not hard failures
- [ ] Testing & revision: infrastructure changes reference testing/validation plans

### 1.7 Evaluation (§164.308(a)(8))
- [ ] Periodic evaluation: compliance scanning is not disabled or bypassed in CI/CD

### 1.8 Business Associate Agreements (§164.308(b))
- [ ] *[org]* New third-party integrations (APIs, SaaS, LLM providers) that touch PHI have BAA references
- [ ] Third-party API calls that transmit PHI use approved, BAA-covered endpoints
- [ ] No PHI sent to services without documented BAA coverage (e.g., unapproved analytics, logging services)

---

## 2. Physical Safeguards (§164.310)

### 2.1 Facility Access Controls (§164.310(a))
- [ ] *[org]* Infrastructure-as-code changes do not expose management interfaces publicly
- [ ] Cloud resource configurations maintain private subnet placement for data stores

### 2.2 Workstation & Device Security (§164.310(b)-(c))
- [ ] No hardcoded file paths to local workstation locations in production code
- [ ] No assumptions about physical device security (e.g., storing keys on disk without encryption)

### 2.3 Device & Media Controls (§164.310(d))
- [ ] Data disposal: temporary files/caches containing PHI are cleaned up (workspace GC, /tmp cleanup)
- [ ] Media re-use: exported data files are scoped and cleaned after processing
- [ ] Accountability: data export endpoints log what was exported, by whom, and when

---

## 3. Technical Safeguards (§164.312)

### 3.1 Access Control (§164.312(a))
- [ ] Unique user identification: all endpoints identify the authenticated user (no anonymous PHI access)
- [ ] Emergency access procedure: break-glass access patterns are logged with elevated audit detail
- [ ] Automatic logoff: session timeouts are configured and not extended beyond policy limits
- [ ] Encryption & decryption: PHI at rest uses AES-256 or equivalent; encryption keys from env/secrets manager

### 3.2 Audit Controls (§164.312(b))
- [ ] PHI reads are logged (who accessed what, when, from which IP/session)
- [ ] PHI writes/modifications are logged with before/after context or change summary
- [ ] Audit logs themselves do not contain PHI in free-text fields (log sanitization)
- [ ] Audit log deletion/modification is prevented (append-only or immutable storage)
- [ ] Log retention: changes do not reduce log retention below required minimums (6 years for HIPAA)

### 3.3 Integrity Controls (§164.312(c))
- [ ] Data integrity: critical health data writes use database transactions
- [ ] Mechanism to authenticate ePHI: checksums or signatures for data imports/exports (if applicable)
- [ ] No silent data truncation or lossy transformations on PHI fields

### 3.4 Person or Entity Authentication (§164.312(d))
- [ ] Authentication required on all new endpoints that access PHI
- [ ] Multi-factor authentication flows are not weakened or bypassed
- [ ] Token validation is server-side; client-supplied tokens are never trusted without verification

### 3.5 Transmission Security (§164.312(e))
- [ ] All external API calls use HTTPS/TLS — no plain HTTP (except localhost)
- [ ] TLS version is not downgraded below 1.2
- [ ] WebSocket connections (if any) use WSS, not WS
- [ ] API responses include appropriate security headers (HSTS, X-Content-Type-Options, etc.)

---

## 4. PHI-Specific Controls

### 4.1 PHI in Code
- [ ] No PHI (names, DOB, SSN, MRN, emails, phone numbers, addresses) in log statements
- [ ] No PHI in comments, string literals, or error messages returned to clients
- [ ] No PHI in URL paths, query parameters, or request headers
- [ ] No PHI in client-side analytics, telemetry, or crash reporting payloads
- [ ] No PHI in AI/LLM prompts without prior sanitization

### 4.2 Minimum Necessary (§164.502(b))
- [ ] Database queries select only required fields (no `SELECT *` on PHI tables)
- [ ] API responses return only fields needed by the consumer
- [ ] Batch operations are scoped to the minimum necessary data set
- [ ] Search/list endpoints enforce pagination to limit data exposure surface

### 4.3 De-identification (§164.514)
- [ ] Data used for analytics, reporting, or AI training is de-identified or aggregated
- [ ] Export/download features strip or redact PHI unless explicitly authorized

### 4.4 Data Retention & Disposal
- [ ] Patient/health data uses soft delete (no hard deletes)
- [ ] Deletion endpoints enforce authorization and audit logging
- [ ] Temporary files, caches, and worker workspaces containing PHI are cleaned up on schedule
- [ ] Database backups and snapshots follow the same retention/destruction policies as live data

---

## 5. Organizational Requirements (§164.314)

### 5.1 Business Associate Contracts
- [ ] *[org]* All subprocessors handling PHI (AWS, LLM providers, EHR APIs) have valid BAAs
- [ ] Code does not route PHI through new third-party services without BAA verification

### 5.2 Group Health Plan Requirements
- [ ] *[org]* N/A for most SaaS — skip unless the change involves group health plan data

---

## 6. Breach Notification (§164.400-414)

- [ ] Breach detection: unauthorized access patterns trigger alerts (not just logs)
- [ ] Breach logging: sufficient metadata is captured to support breach investigation (who, what, when, scope)
- [ ] No changes suppress or delay breach notification mechanisms

---

## 7. Telehealth-Specific (if applicable)

- [ ] Recording requires explicit consent from all parties before activation
- [ ] Video/audio tokens are not stored in localStorage — use httpOnly cookies or in-memory only
- [ ] Telehealth tokens have explicit expiry (max 4 hours)
- [ ] Visit start, end, duration, and participant join/leave events are audit-logged
- [ ] Screen sharing warns participants when PHI is visible

---

## Output markers

For each item above, emit a structured marker:

```
<!-- SECURE_ITEM:pass|warn|fail:§Section:Check Name:Detail about the finding -->
```
