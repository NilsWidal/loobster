# ISO/IEC 27001:2022 Checklist (Annex A controls)

Review each item against the code diff. For each, assign: **PASS**, **WARN**, or **FAIL**.
Items marked *[org]* may not be directly visible in the diff — verify the organizational control exists.
Control IDs reference the ISO/IEC 27001:2022 Annex A themes (Organizational 5.x, People 6.x, Physical 7.x, Technological 8.x).

---

## 5 — Organizational controls

### 5.7 Threat intelligence / 5.8 Security in project management
- [ ] New features handling sensitive data include threat-model considerations (even as comments)
- [ ] *[org]* Security requirements are considered in the change's design (ADR / ticket reference)

### 5.10 Acceptable use / 5.14 Information transfer
- [ ] No sensitive data transferred over unencrypted channels (HTTP, plaintext)
- [ ] Data shared with third parties is limited to what is necessary

### 5.15–5.18 Access control, identity & authentication
- [ ] Access decisions are enforced server-side (no client-only authorization)
- [ ] Least privilege: new roles/scopes grant only what is required
- [ ] No hardcoded credentials, default passwords, or shared accounts

### 5.23 Cloud services / 5.31 Legal & regulatory
- [ ] *[org]* New cloud services / subprocessors have a documented security evaluation
- [ ] Changes respect applicable regulatory requirements for the data handled

### 5.33 Protection of records
- [ ] Records/audit data are not deleted by hard delete where retention applies (soft delete / archival)

---

## 6 — People controls

### 6.3 Awareness / 6.8 Reporting events
- [ ] Security-relevant code includes the "why" so reviewers can assess it
- [ ] *[org]* A path exists to report a weakness found in this change (issue tracker)

---

## 7 — Physical controls

### 7.x Physical & environmental
- [ ] *[org]* Infrastructure changes do not expose management interfaces publicly (no `0.0.0.0/0` on admin ports; databases not publicly accessible)

---

## 8 — Technological controls

### 8.1 User endpoint / 8.2–8.5 Privileged access, restriction, secure authentication
- [ ] Authentication checks are present on all new protected endpoints
- [ ] Session/token handling is correct (expiry, rotation, secure + httpOnly cookies)
- [ ] No privilege escalation paths (a user cannot act on another tenant's/user's data)

### 8.8 Management of technical vulnerabilities
- [ ] Dependencies are pinned (no floating versions) and free of known-vulnerable pins introduced by this change
- [ ] No use of deprecated/insecure crypto (MD5, SHA1 for security, ECB, hardcoded IVs)

### 8.9 Configuration management / 8.10 Information deletion
- [ ] No secrets or credentials committed in code or config
- [ ] Deletion of sensitive data is honored (no orphaned copies; deletes propagate)

### 8.11 Data masking / 8.12 Data leakage prevention
- [ ] Sensitive fields are masked/redacted in logs, errors, and analytics
- [ ] Error responses do not leak internal details (stack traces, queries, secrets)

### 8.15 Logging / 8.16 Monitoring
- [ ] Security-relevant actions (auth, access to sensitive data, config changes) are logged
- [ ] Logs do not contain secrets or unmasked sensitive data

### 8.24 Use of cryptography
- [ ] Data in transit uses TLS; data at rest sensitive fields are encrypted
- [ ] Strong algorithms only; keys are not hardcoded

### 8.25–8.28 Secure development lifecycle, secure coding, security testing, outsourced development
- [ ] Input is validated at all new API/trust boundaries
- [ ] No injection vectors (SQL/NoSQL/command/template) — parameterized queries, escaped output
- [ ] Output encoding prevents XSS in any new rendered content
- [ ] *[org]* Change went through review before merge (PR review / branch protection)

### 8.29 Security testing in development and acceptance
- [ ] Behavior changes ship with a runnable automated test

---

## Notes
- FAIL items should block commit/push — flag clearly.
- *[org]* items are tracked in `org-controls-audit.md` on the periodic audit schedule; they do not block but must be reviewed.
- This checklist focuses on Annex A controls that are visible in or relevant to a code diff; full ISO 27001 certification covers the management system (Clauses 4–10) separately.
