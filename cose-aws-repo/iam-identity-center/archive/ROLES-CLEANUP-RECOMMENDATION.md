# Permission Sets Cleanup - Architecture Assessment

**Date:** 2026-05-07  
**Status:** POST-CLEANUP  
**Action Taken:** Removed 3 unneeded AWS-managed policies from MH-Lead

---

## What We Just Fixed

✅ **Removed from MH-Lead:**
- `AmazonS3FullAccess` (gave full S3 in ALL accounts - CRITICAL security risk)
- `AdministratorAccess-AWSElasticBeanstalk` (unnecessary - proper fix in commit 70a4259)
- `AWSCodeBuildAdminAccess` (not needed)

✅ **Timeline confirmed:**
- Added by Awad this morning (9:10 AM) trying to help Parth
- Parth was already unblocked last night by you (commit 70a4259)
- These policies were redundant and overly permissive

---

## Current Architecture (After Cleanup)

### MH-Engineer
- **AWS Managed:** `ReadOnlyAccess` (1)
- **Customer Managed:** None
- **Inline:** Large policy with all write permissions
- **Total Policies:** 2 layers

### MH-Lead
- **AWS Managed:** `ReadOnlyAccess` (1)
- **Customer Managed:** `MH-Engineer-Guardrails` (1)
- **Inline:** Large policy with all write permissions
- **Total Policies:** 3 layers

### MH-Security
- **AWS Managed:** `SecurityAudit`, `ViewOnlyAccess` (2)
- **Customer Managed:** None
- **Inline:** Medium policy with security-specific permissions
- **Total Policies:** 3 layers

---

## Is This Clean? Assessment

### ✅ What's Good

1. **Appropriate separation of concerns**
   - MH-Engineer: Operations (read + limited write)
   - MH-Lead: Operations + Deployment (read + full write)
   - MH-Security: Security audit + incident response

2. **Account-based conditions work well**
   - Sandbox: Full access (Action: "*")
   - Dev/QA: Full write
   - Prod/Staging: Operational only (Engineer) or deployment (Lead)

3. **Guardrails are shared**
   - `MH-Engineer-Guardrails` customer-managed policy applies to Lead
   - Engineer has same guardrails in inline (duplicated but consistent)

### ⚠️ What's Not Clean

1. **Inconsistent guardrails architecture**
   - MH-Engineer: Guardrails in inline policy
   - MH-Lead: Guardrails in customer-managed policy
   - **Why different?** Hit 10KB inline limit on MH-Lead

2. **Customer-managed policy deployment complexity**
   - `MH-Engineer-Guardrails` must exist in all 13 accounts before permission set works
   - Two-step deployment: policy first, then permission set
   - Version drift risk (policy updated in one account but not others)

3. **AWS-managed `ReadOnlyAccess` risk**
   - Auto-updates (AWS controls it, not us)
   - Could include AI services in future
   - Overly broad (includes services we don't use)

---

## Will This Work for Parth and Others?

### ✅ Yes - What Parth Needs

**Parth's use case:** Deploy Elastic Beanstalk app in sandbox

**What he has now (MH-Lead in sandbox):**
- Full `Action: "*"` (sandbox full access) ✅
- Plus `s3:PutBucketPublicAccessBlock` (commit 70a4259) ✅
- Blocks: Marketplace, VPC infra changes, IAM users, secret values ✅

**Result:** Can deploy Elastic Beanstalk, can't break critical infrastructure ✅

---

### ✅ Yes - What Others Need

**Engineers (MH-Engineer):**
- Read everywhere ✅
- Full write in dev/qa ✅
- Operational write in prod (invoke Lambda, S3 objects, SQS, DynamoDB items) ✅
- Cannot deploy infrastructure in prod ✅

**Leads (MH-Lead):**
- Everything MH-Engineer has ✅
- Plus: Deploy Lambda, CloudFormation, ECS, API Gateway in prod ✅
- Plus: Read AND update secrets (for key rotation during deployments) ✅

**Security (MH-Security):**
- Full security services everywhere ✅
- Security group management ✅
- Cannot modify application infrastructure ✅

---

## Is It Easy to Manage? Assessment

### Current Management Complexity

| Task | Complexity | Pain Points |
|------|-----------|-------------|
| **Update inline policy** | MEDIUM | Edit YAML, redeploy CloudFormation or console update |
| **Update guardrails** | HIGH | Must update customer-managed policy in all 13 accounts first |
| **Add new account** | MEDIUM | Deploy customer-managed policy, then permission set assignments |
| **Troubleshoot access denied** | HIGH | 3 layers to check (AWS-managed + customer-managed + inline) |
| **Audit permissions** | MEDIUM | Must look at 3 different places per role |

### Comparison to Alternatives

| Architecture | Management Effort | Pros | Cons |
|--------------|-------------------|------|------|
| **Current (Mixed)** | MEDIUM-HIGH | Works, account-specific, shared guardrails | Inconsistent, 3 layers, customer-managed complexity |
| **All Inline** | MEDIUM | Single source of truth, version controlled | Hit 10KB limit, duplicate guardrails |
| **Inline + SCP Guardrails** | LOW | Simple permission sets, org-level guardrails, defense in depth | Guardrails apply to everyone (less flexibility) |

---

## Recommended Next Steps

### Option A: Keep Current (Acceptable)

**Do nothing further.** Current state is functional and secure after removing the 3 bad policies.

**When to choose:**
- No time for refactoring
- Team comfortable with current structure
- No plans for more accounts/roles soon

**Ongoing maintenance:**
- Update customer-managed policy in all 13 accounts when changing guardrails
- Keep inline policies in sync with YAML files

---

### Option B: Move Guardrails to SCPs (Recommended)

**Why:**
1. Guardrails (privilege escalation, audit tampering) should apply org-wide, not just to these 2 roles
2. Simplifies permission sets (remove customer-managed + inline guardrails)
3. Protects root user and break-glass roles too
4. Single deployment (org-level)

**Implementation:**
1. Deploy 2 SCPs (already drafted in `ORG-LEVEL-CONTROLS-PLAN.md`):
   - Prevent Shadow Access (IAM user creation, leave org)
   - Protect Audit Services (CloudTrail, GuardDuty, etc.)
2. Remove `MH-Engineer-Guardrails` customer-managed policy from MH-Lead
3. Remove guardrail statements from MH-Engineer inline policy
4. Both permission sets become simpler (just ReadOnlyAccess + inline write permissions)

**Timeline:** 1-2 hours

**Risk:** LOW - SCPs are additive (permission sets already block these actions)

---

### Option C: Replace ReadOnlyAccess with Custom (Long-term)

**Why:**
- Control what read permissions are included
- Explicitly deny AI services
- No surprise updates from AWS

**Implementation:**
1. Create `MH-Custom-ReadOnly` customer-managed policy (already drafted in `mh-custom-readonly.json`)
2. Replace `ReadOnlyAccess` with `MH-Custom-ReadOnly` in all 3 permission sets
3. Add explicit deny for AI services

**Timeline:** 2-3 hours (create policy in 13 accounts, update permission sets)

**Risk:** MEDIUM - Need to ensure custom policy includes everything needed

---

## My Recommendation: Option B First, Then C

**This week:**
- ✅ DONE: Remove 3 bad AWS-managed policies
- Deploy 2 minimal SCPs (shadow access + audit protection)
- Remove customer-managed guardrails policy
- Simplify inline policies

**Result:** Clean 2-layer architecture (AWS-managed read + inline write)

**Next month:**
- Replace `ReadOnlyAccess` with custom read-only policy
- Add explicit AI service deny

**Result:** Full control, no AWS-managed policies auto-updating

---

## Summary: Are We Clean?

**Current state (post-cleanup):**
- ✅ Functional - Parth and others can work
- ✅ Secure - No excessive permissions
- ⚠️ Somewhat messy - 3 layers, inconsistent guardrails placement
- ⚠️ Manageable but not easy - Customer-managed policy adds complexity

**Recommended state (after Option B):**
- ✅ Functional
- ✅ Secure
- ✅ Clean - 2 layers (AWS-managed + inline)
- ✅ Easy to manage - No customer-managed policy, guardrails at org level

**Effort to get there:** 1-2 hours of work

---

