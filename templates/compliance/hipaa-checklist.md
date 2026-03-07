# HIPAA Security Checklist

Review each item against the code diff. For each, assign: PASS, WARN, or FAIL.

## PHI in Code
- [ ] No PHI (names, DOB, SSN, MRN, emails, phone numbers, addresses) in log statements
- [ ] No PHI in comments or string literals
- [ ] No PHI in error messages returned to clients
- [ ] No PHI in URL paths or query parameters

## Encryption
- [ ] Data at rest: sensitive fields are encrypted before storage (no plaintext PHI in database)
- [ ] Data in transit: all external API calls use HTTPS/TLS
- [ ] Encryption keys are not hardcoded; loaded from environment or secret manager

## Access Control
- [ ] Authentication required on all new endpoints
- [ ] Authorization checks enforce role-based access
- [ ] Tenant isolation: queries scoped to authenticated tenant (no cross-tenant data leakage)
- [ ] API responses do not include data beyond what the requester is authorized to see

## Audit Trail
- [ ] Data reads of PHI are logged (who accessed what, when)
- [ ] Data writes/modifications are logged with before/after values or change summary
- [ ] Audit logs do not themselves contain PHI in free-text fields

## Minimum Necessary
- [ ] Database queries select only required fields (no `SELECT *` on PHI tables)
- [ ] API responses return only fields needed by the consumer
- [ ] Batch operations are scoped to the minimum necessary data set

## Data Retention & Deletion
- [ ] Patient/health data uses soft delete (no hard deletes)
- [ ] Deletion endpoints enforce authorization and audit logging
- [ ] Temporary files or caches containing PHI are cleaned up

## Output markers
For each item above, emit a structured marker:
```
<!-- SECURE_ITEM:pass|warn|fail:Check Name:Detail about the finding -->
```
