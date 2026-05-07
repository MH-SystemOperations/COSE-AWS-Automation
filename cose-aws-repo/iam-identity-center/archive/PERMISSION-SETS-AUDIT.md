# Permission Sets Audit - Current State vs. Design

**Date:** 2026-05-07  
**Auditor:** Claude + Micah Review  
**Scope:** MH-Engineer, MH-Lead, MH-Security

---

## Summary of Findings

🔴 **CRITICAL:** MH-Lead has 3 unplanned AWS managed policies granting excessive permissions  
🟡 **WARNING:** Inconsistent architecture (inline + customer-managed + AWS-managed policies)  
🟢 **OK:** MH-Engineer and MH-Security match design

---

## Detailed Findings

### MH-Engineer ✅ **Matches Design**

**AWS Managed Policies (1):**
- `ReadOnlyAccess` ✅ As designed

**Customer Managed Policies:**
- None (guardrails moved to inline in commit 00ec7fe)

**Inline Policy:**
- Full inline policy with all permissions ✅ As designed

**Issues:** None

---

### MH-Lead 🔴 **CRITICAL DRIFT**

**AWS Managed Policies (4):**
1. `ReadOnlyAccess` ✅ As designed
2. `AWSCodeBuildAdminAccess` ❌ **UNPLANNED**
3. `AdministratorAccess-AWSElasticBeanstalk` ❌ **UNPLANNED**
4. `AmazonS3FullAccess` ❌ **UNPLANNED**

**Customer Managed Policies (1):**
- `MH-Engineer-Guardrails` ✅ As designed (commit 035d4a7)

**Inline Policy:**
- Full inline policy ✅ As designed

**Issues:**

#### Issue #1: `AmazonS3FullAccess`
**What it grants:**
```json
{
  "Action": [
    "s3:*"
  ],
  "Resource": "*"
}
```

**Risk:** CRITICAL
- Full S3 access in ALL 13 accounts (not scoped to sandbox/dev/qa)
- Can delete production buckets
- Can make buckets public
- Can disable encryption
- Bypasses all inline policy S3 restrictions

**How this happened:** Unknown - not in Git history

---

#### Issue #2: `AdministratorAccess-AWSElasticBeanstalk`
**What it grants:**
- Full Elastic Beanstalk admin
- PassRole to Elastic Beanstalk service
- EC2, Auto Scaling, ELB, CloudFormation for Elastic Beanstalk resources
- S3 access for Elastic Beanstalk artifacts

**Risk:** HIGH
- Account-level admin for Elastic Beanstalk
- Can create resources with any IAM role (PassRole)
- Broader than needed for simple deployments

**How this happened:** Likely added to fix Elastic Beanstalk deployment issue in sandbox

**What was actually needed:** Just `elasticbeanstalk:*` + `s3:PutBucketPublicAccessBlock` (which we fixed in commit 70a4259)

---

#### Issue #3: `AWSCodeBuildAdminAccess`
**What it grants:**
```json
{
  "Action": [
    "codebuild:*"
  ],
  "Resource": "*"
}
```

Plus IAM PassRole for CodeBuild service.

**Risk:** MEDIUM-HIGH
- Can create CodeBuild projects with arbitrary IAM roles
- Can modify existing build projects (security risk)
- Not scoped to specific accounts

**How this happened:** Unknown - CodeBuild not mentioned in requirements

---

### MH-Security ✅ **Matches Design**

**AWS Managed Policies (2):**
1. `SecurityAudit` ✅ As designed
2. `ViewOnlyAccess` ✅ As designed

**Customer Managed Policies:**
- None

**Inline Policy:**
- Security-specific inline policy ✅ As designed

**Issues:** None

---

## Architecture Inconsistency Analysis

### Current State (Mixed Architecture)

| Permission Set | AWS Managed | Customer Managed | Inline | Total Complexity |
|----------------|-------------|------------------|--------|------------------|
| MH-Engineer | 1 (ReadOnlyAccess) | 0 | Large inline | LOW |
| MH-Lead | 4 (Read + 3 unplanned) | 1 (Guardrails) | Large inline | **HIGH** |
| MH-Security | 2 (Security + ViewOnly) | 0 | Medium inline | MEDIUM |

**Problems with this architecture:**
1. **MH-Lead has 3 layers:** AWS-managed + customer-managed + inline (confusing)
2. **AWS-managed policies auto-update** - we don't control what's in them
3. **Guardrails as customer-managed policy** - requires deployment to all 13 accounts, version sync issues
4. **Inline policy limits** - Hit 10KB limit (reason we moved guardrails out)

---

## Git History: How We Got Here

### Commit Timeline

1. **d8f61ce** (Initial): Created MH-Engineer/MH-Lead with inline policies only
2. **00ec7fe** (Refactor): Converted guardrails to inline (in both roles)
3. **3157730** (WIP): Tried to add guardrails as customer-managed (hit 10KB inline limit)
4. **035d4a7** (Fix): Moved guardrails to customer-managed policy (closed security gap)
5. **70a4259** (Fix): Added `s3:PutBucketPublicAccessBlock` to inline for Elastic Beanstalk

**Missing from Git:** When/how the 3 AWS-managed policies were added to MH-Lead

---

## Recommended Architecture (Clean Slate)

### Option 1: All Inline (Simplest)

**Structure:**
- AWS Managed: 1 (ReadOnlyAccess) - provides baseline read everywhere
- Inline: All write permissions + guardrails

**Pros:**
- ✅ Single source of truth
- ✅ Version controlled in Git
- ✅ Deployed atomically with permission set

**Cons:**
- ❌ 10KB inline limit (we hit this)
- ❌ Guardrails duplicated across MH-Engineer and MH-Lead

---

### Option 2: Inline Write + Customer-Managed Guardrails (Current for MH-Lead)

**Structure:**
- AWS Managed: 1 (ReadOnlyAccess)
- Customer Managed: 1 (Guardrails shared across Engineer + Lead)
- Inline: All write permissions

**Pros:**
- ✅ Guardrails shared (DRY principle)
- ✅ Avoids 10KB inline limit

**Cons:**
- ❌ Customer-managed policy must exist in all 13 accounts before permission set deploy
- ❌ Two-step deployment (policy first, then permission set)
- ❌ Version drift risk (policy updated in one account but not others)

---

### Option 3: Service Control Policy (SCP) Guardrails (Recommended)

**Structure:**
- AWS Managed: 1 (ReadOnlyAccess)
- Inline: All write permissions
- **SCP at org level: Guardrails (blocks privilege escalation, audit tampering, etc.)**

**Pros:**
- ✅ Guardrails apply to ALL principals (not just MH-Engineer/MH-Lead)
- ✅ Single deployment (org-level)
- ✅ Defense in depth (protects root user, break-glass roles)
- ✅ Avoids inline 10KB limit
- ✅ Permission sets become simpler

**Cons:**
- ❌ SCPs apply org-wide (less flexibility per role)
- ❌ Can't have different guardrails for Engineer vs. Lead

**Why this is better:**
- Guardrails (privilege escalation, audit tampering) should apply to EVERYONE, not just these 2 roles
- Moves guardrails to correct layer (org-level, not permission-set-level)
- Aligns with the SCP plan we already drafted

---

## What Needs to Happen

### Immediate Actions (This Week)

#### 1. Remove Unplanned AWS Managed Policies from MH-Lead

```bash
# Remove AmazonS3FullAccess
aws sso-admin detach-managed-policy-from-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223f99c07c1a588 \
  --managed-policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --profile mh-ops

# Remove AdministratorAccess-AWSElasticBeanstalk
aws sso-admin detach-managed-policy-from-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223f99c07c1a588 \
  --managed-policy-arn arn:aws:iam::aws:policy/AdministratorAccess-AWSElasticBeanstalk \
  --profile mh-ops

# Remove AWSCodeBuildAdminAccess
aws sso-admin detach-managed-policy-from-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223f99c07c1a588 \
  --managed-policy-arn arn:aws:iam::aws:policy/AWSCodeBuildAdminAccess \
  --profile mh-ops

# Reprovision to all accounts
aws sso-admin provision-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223f99c07c1a588 \
  --target-type ALL_PROVISIONED_ACCOUNTS \
  --profile mh-ops
```

**Test after removal:**
- ✅ Can still deploy to Elastic Beanstalk in sandbox (commit 70a4259 fixed this properly)
- ✅ Prod S3 access scoped correctly (no longer full S3:*)

---

#### 2. Add Missing Permissions to Inline (If Needed)

If Elastic Beanstalk deployments break after removing `AdministratorAccess-AWSElasticBeanstalk`, add to inline:

```json
{
  "Sid": "ElasticBeanstalkSandbox",
  "Effect": "Allow",
  "Action": [
    "elasticbeanstalk:*"
  ],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:PrincipalAccount": "123185598779"
    }
  }
}
```

**Note:** We already have full `Action: "*"` in sandbox, so this might be redundant.

---

### Short-Term (Next 2 Weeks)

#### 3. Document Current Architecture

Update `PERMISSIONS-SUMMARY-FOR-ARCHITECT.md`:
- Note that MH-Lead uses customer-managed guardrails policy
- Document deployment order (policy must exist first)
- Add troubleshooting for "policy not found" errors

---

#### 4. Deploy Guardrails as SCP (Recommended Long-Term)

Follow `ORG-LEVEL-CONTROLS-PLAN.md`:
1. Deploy SCP with guardrails (privilege escalation, audit tampering)
2. Remove `MH-Engineer-Guardrails` customer-managed policy from MH-Lead
3. Remove guardrails from inline policies (now redundant with SCP)

**Benefits:**
- Simpler permission sets
- Defense in depth (SCP protects root user too)
- Single org-level deployment

---

### Long-Term (Next Month)

#### 5. Replace ReadOnlyAccess with Custom Policy

AWS `ReadOnlyAccess` policy:
- Auto-updates (we don't control it)
- Overly broad (includes services we don't use)
- Could include AI services in future

Replace with custom read-only policy (see `mh-custom-readonly.json`):
- Explicit list of allowed read actions
- Explicit deny for AI services
- Under our version control

---

## Questions for Team

1. **Who added the 3 AWS-managed policies to MH-Lead?**
   - Was it for Elastic Beanstalk deployment testing?
   - Are they still needed? (Likely no - commit 70a4259 fixed it properly)

2. **Do we use CodeBuild anywhere?**
   - If no → Remove `AWSCodeBuildAdminAccess` immediately
   - If yes → Scope to specific accounts/projects

3. **Architecture preference:**
   - Option 2: Keep customer-managed guardrails policy?
   - Option 3: Move guardrails to SCPs (recommended)?

4. **Deployment process:**
   - Should permission sets be deployed via CloudFormation (IaC)?
   - Or manual via console/CLI?
   - Current state: CFN templates exist but manual deployment happening

---

## Appendix: Permission Set ARNs

- **MH-Engineer:** `arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223e550ce22c566`
- **MH-Lead:** `arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223f99c07c1a588`
- **MH-Security:** `arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-3c2249ba3b58c3ab`

---

