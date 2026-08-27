# Organizational Controls — Periodic Audit Checklist (TEMPLATE)

These controls **cannot be verified from code diffs** — they require manual verification on a schedule. `/secure` skips them and points here so a green diff can't be mistaken for a passing org posture.

> **This is a blank template — fill it in for YOUR organization before relying on it.**
> Nothing below is pre-verified. Set the review dates, replace the example `How to Verify`
> commands (the AWS/Linear ones are illustrative of one stack, not your stack), and only
> mark a row `PASS` once you have actually verified it. Do not ship it with someone else's
> results.

**Review cadence:** Quarterly (suggested)
**Last reviewed:** _(not yet — set on first audit)_
**Next review:** _(set on first audit)_

---

## HIPAA — Administrative & Physical Safeguards

### §164.308 Administrative

| Control | Requirement | How to Verify | Status | Last Verified |
|---------|-------------|---------------|--------|---------------|
| §164.308(a)(4) | Healthcare clearinghouse function isolation | N/A unless your org is a clearinghouse | | |
| §164.308(a)(5) | Security awareness training for workforce | Check training records for all team members | | |
| §164.308(b) | BAA signed with all PHI-handling vendors | Review your BAA registry — verify all entries are current | | |

### §164.310 Physical Safeguards

| Control | Requirement | How to Verify | Status | Last Verified |
|---------|-------------|---------------|--------|---------------|
| §164.310(a) | Infrastructure does not expose management interfaces publicly | Audit cloud security groups for `0.0.0.0/0` on management ports; confirm databases are not publicly accessible and sit in private subnets | | |
| §164.310(b)-(c) | Workstation security policies | Verify team laptops have disk encryption (FileVault/BitLocker), screen lock, and remote wipe | | |

---

## SOC 2 — Governance & Organizational Controls

| Control | Requirement | How to Verify | Status | Last Verified |
|---------|-------------|---------------|--------|---------------|
| CC1.1 | Code of conduct / integrity | Verify employee handbook includes security expectations | | |
| CC1.2 | Board/management oversight of security | Verify security review is part of leadership meetings | | |
| CC1.3 | CI/CD and infra changes reviewed by authorized personnel | Check branch protection: `gh api repos/<owner>/<repo>/branches/main/protection` | | |
| CC3.1 | Risk assessment for new features | Verify threat modeling happens during planning (issue templates, ADRs) | | |
| CC6.1 | Least-privilege IAM policies | Audit cloud IAM for over-permissioned roles | | |
| CC6.4 | Physical access to cloud infrastructure | Verify your cloud provider's SOC 2 Type II report is current (inherited control) | | |
| CC8.1 | PR review before merge | Check branch protection: `Require pull request reviews before merging` is enabled | | |

---

## HITRUST — Organizational & HR Controls

| Control | Requirement | How to Verify | Status | Last Verified |
|---------|-------------|---------------|--------|---------------|
| 00.a | Security policies referenced in changes | Verify your repo's agent instructions (CLAUDE.md / AGENTS.md) mandate `/review-code` + `/secure` | | |
| 02.a | Access control changes reviewed by security-aware personnel | Check CODEOWNERS covers security-critical paths | | |
| 02.e | Security awareness — code includes control purpose comments | Spot-check 5 security-critical files for inline compliance comments | | |
| 04.a | Changes reference applicable security policy | Verify agent instructions reference compliance requirements | | |
| 05.a | Security-critical changes have reviewer approval | Same as CC8.1 — check branch protection | | |
| 05.i | Third-party integrations have documented security evaluation | Review your BAA registry for completeness | | |
| 05.i | BAAs exist for PHI-handling third parties | Cross-reference running services with the BAA registry | | |
| 06.a | HIPAA and state privacy law compliance | Legal review of terms, privacy policy, BAA template | | |
| 07.a | New infrastructure resources tagged and inventoried | Audit resource tagging in your cloud account | | |
| 07.b | Services/components have designated owners | Verify CODEOWNERS covers all directories | | |
| 08.a | Cloud provider physical security | Verify your cloud provider's SOC 2 Type II report is available and current | | |
| 10.h | Changes go through PR review | Same as CC8.1 | | |
| 11.b | Incident response procedures not weakened | Review that an incident response runbook exists and is current | | |

---

## Token-compression hook (Option D, on by default) — data-path control

Loobster ships a token-compression hook (`hooks/hooks.json` → `bin/headroom-compress.py`) that is **enabled by default** and runs large tool outputs through a compressor before they reach the model. It has two tiers: **Tier 2** (`bin/lite_crush.py`) is **first-party, pure-stdlib, local-only — no network, no disk writes** — and runs even when nothing is installed; **Tier 1** is a locally-installed [headroom](https://github.com/headroomlabs-ai/headroom), preferred when importable. **Because it is on by default, a compressor reads tool outputs (possible PHI) on every matching tool call** — treat this as an organizational control. On PHI repos, **set `LOOBSTER_HEADROOM=0` to disable all compression** until a data-path review (or `LOOBSTER_LITE_CRUSH=0` to drop only the first-party tier while headroom is reviewed).

| Control | Requirement | How to Verify | Status | Last Verified |
|---------|-------------|---------------|--------|---------------|
| 05.i / §164.308(b) | The default-on compression hook is covered by a security review and (if it processes PHI) a BAA or local-only attestation | In PHI environments, set `LOOBSTER_HEADROOM=0` unless reviewed. Tier 2 (lite-crush) is first-party and network-free; Tier 1 (headroom, if installed) runs locally — verify the headroom version and that its CCR original-store is encrypted/GC'd per policy | | |
| 04.a | Running the default-on hook on PHI is a reviewed, documented decision | Verify that the first-party crusher reading tool outputs is acceptable, and the PHI-at-rest implications of headroom's CCR store (Tier 1) are addressed — or that `LOOBSTER_HEADROOM=0` is set on PHI repos | | |

---

## Shared signals hub — data-path control

The signals hub (`signals/*.md`, `commands/signals.md`) is a **committed, team-shared** data sink. It is safe only while signals stay **non-PHI summaries** — the load-bearing control.

| Control | Requirement | How to Verify | Status | Last Verified |
|---------|-------------|---------------|--------|---------------|
| §164.514 / 05.i | Shared signals contain no PHI | `python3 bin/signals-build.py signals --strict` exits 0 (no PHI-shaped or malformed signals); spot-check `signals/INDEX.md` | enforced in `/secure` | |
| 04.a | Signals→GitHub Pages publishing is a reviewed decision | If Pages is enabled: confirm the published board is genuinely private (private repo on GitHub Enterprise Cloud) or non-PHI. Never a public board for PHI work — `/team-setup` refuses this by default. | OFF by default | |

---

## How to Run This Audit

1. Open this file.
2. For each row without a recent "Last Verified" date, perform the verification.
3. Update the Status and Last Verified columns.
4. If any item fails, file a ticket with priority based on severity.
5. Commit the updated file.

### Example verification commands (adapt to your stack)

```bash
# Branch protection
gh api repos/<owner>/<repo>/branches/main/protection 2>&1 | jq '.required_pull_request_reviews'

# (AWS example) security groups open to the world
aws ec2 describe-security-groups --profile <prod-profile> \
  --query 'SecurityGroups[?IpPermissions[?IpRanges[?CidrIp==`0.0.0.0/0`]]].[GroupId,GroupName]' --output table

# (AWS example) IAM policies with wildcard resources
aws iam get-account-authorization-details --profile <prod-profile> --filter LocalManagedPolicy \
  --query 'Policies[].PolicyVersionList[].Document.Statement[?Resource==`*`]' --output json | head -50

# (AWS example) managed databases must not be publicly accessible
aws rds describe-db-instances --profile <prod-profile> \
  --query 'DBInstances[].[DBInstanceIdentifier,PubliclyAccessible]' --output table
```

---

## Quarterly Audit Record

_(fill in one row per completed audit)_

| Quarter | Reviewer | Items Verified | Issues Found | Tickets Created |
|---------|----------|---------------|-------------|-----------------|
| | | | | |
