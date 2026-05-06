# Account to Environment Mapping

**Date**: 2026-05-06  
**Status**: Account-based permissions (tag-based deferred until account restructure)

---

## Current Implementation: Account-Based Access Control

MH-Engineer and MH-Lead use `aws:PrincipalAccount` conditions to grant permissions based on which AWS account you're accessing, not resource tags.

**Why account-based for now:**
- Simpler IAM policies (no tag enforcement complexity)
- Faster authorization (no tag lookups)
- More reliable (account IDs don't change)
- AWS best practice (separate blast radius)
- Current account structure doesn't cleanly align to environments yet

**Future state:** When accounts are restructured to align with environments (one account per team per environment), we may revisit tag-based access for fine-grained control within accounts.

---

## Environment Groupings

### 🟢 Sandbox (Full Access - Experiment Freely)
**Account**: 123185598779 - Platform Sandbox

**Permissions**:
- `Action: "*"` (everything allowed)
- **Blocked**: AWS Marketplace, VPC infrastructure changes, IAM user/policy creation, reading secret values
- **Purpose**: Safe experimentation without affecting other environments

---

### 🔵 Dev/QA (Full Write - Build & Test)
**Accounts**:
- 201799325713 - Platform Data Dev
- 808468589041 - Platform Data QA
- 686255955782 - Platform Digital Tools Dev
- 593793032905 - Platform Digital Tools QA

**Permissions (MH-Engineer & MH-Lead)**:
- ✅ Full: Lambda, S3, DynamoDB, Glue, Athena, CloudWatch, ECS, ECR, EC2, RDS (2 accounts only), CloudFormation
- ✅ IAM role creation (with `dev_boundary` permissions boundary required)
- ✅ Secrets Manager full access
- ✅ Security group management
- ✅ Load balancer & Auto Scaling management
- ❌ Blocked by guardrails: Expensive instances, IAM users, audit tampering

**Current Gaps**:
- RDS only available in 201799325713 and 686255955782 (not QA accounts 808468589041, 593793032905)
- Could add if QA needs database testing

---

### 🟡 Staging (Not Yet Defined)
**Accounts**:
- 209479269442 - Platform Digital Tools Staging

**Current Status**: Not included in dev/qa group, not included in prod group
**Permissions**: ReadOnlyAccess only (via managed policy)

**Decision needed**: Should staging be:
- Option A: Treated like dev/qa (full write access for testing)?
- Option B: Treated like prod (operational access, deployment via MH-Lead only)?
- Option C: Hybrid (full write for some services, restricted for others)?

---

### 🔴 Production (Operational + Deployment)
**Accounts**:
- 971318514578 - Platform Data Prod
- 266565038828 - MH System Operations

**MH-Engineer Permissions** (Operational):
- ✅ Lambda invoke (not create/update)
- ✅ S3 put/delete objects
- ✅ SQS all operations (purge queues, redrive DLQ)
- ✅ DynamoDB item operations (not table creation)
- ✅ Glue/Athena/DataBrew/Step Functions start/stop (not modify definitions)
- ✅ Secrets Manager read (GetSecretValue, UpdateSecret)
- ✅ CloudWatch dashboards, logs
- ✅ Cognito resource server management
- ❌ NO: EC2/RDS/ECS operations, CloudFormation, Lambda CRUD

**MH-Lead Additional Permissions** (Deployment):
- ✅ Lambda CRUD (create, update code, delete)
- ✅ CloudFormation full
- ✅ API Gateway full
- ✅ ECS full (deploy task definitions, update services)
- ✅ ECR full
- ✅ EventBridge/Scheduler full
- ✅ IAM role creation (with `dev_boundary` permissions boundary)

**Current Gaps**:
- MH-Engineer cannot manage ECS services in prod (restart, scale)
- Consider adding: `ecs:UpdateService`, `ecs:RunTask`, `ecs:StopTask` for incident response

---

### ⚪ Other Accounts (Not Yet Classified)
**Accounts**:
- 476114142697 - Platform Digital Tools Prod
- 339712701706 - Pharmacy Prod
- 126693536052 - CostAnalytics-DataCollection
- 648300264365 - OurHealth Dev
- 016592542065 - DevEx

**Current Status**: Assigned MH-Engineer & MH-Lead, but permissions only give ReadOnlyAccess
**Permissions**: Only the managed `ReadOnlyAccess` policy applies (no write permissions via inline policies)

**Decision needed**: Classify each account as dev/qa/staging/prod to grant appropriate permissions

---

## Permission Matrix

| Permission | Sandbox | Dev/QA | Staging | Prod (Engineer) | Prod (Lead) |
|------------|---------|--------|---------|----------------|-------------|
| **Compute** |
| EC2 instances | ✅ Full | ✅ Full | ❓ | ❌ Read-only | ❌ Read-only |
| ECS tasks | ✅ Full | ✅ Full | ❓ | ❌ None | ✅ Full |
| Lambda | ✅ Full | ✅ Full | ❓ | ⚠️ Invoke only | ✅ Full CRUD |
| **Storage** |
| S3 objects | ✅ Full | ✅ Full | ❓ | ✅ Put/Delete | ✅ Put/Delete |
| S3 buckets | ✅ Create/Delete | ✅ Create/Delete | ❓ | ❌ Read-only | ❌ Read-only |
| DynamoDB items | ✅ Full | ✅ Full | ❓ | ✅ Full | ✅ Full |
| DynamoDB tables | ✅ Full | ✅ Full | ❓ | ❌ Read-only | ❌ Read-only |
| RDS | ✅ Full | ⚠️ 2 accounts only | ❓ | ❌ Read-only | ❌ Read-only |
| **Data** |
| Glue jobs | ✅ Full | ✅ Full | ❓ | ⚠️ Start/Stop only | ⚠️ Start/Stop only |
| Athena queries | ✅ Full | ✅ Full | ❓ | ✅ Full | ✅ Full |
| DataBrew jobs | ✅ Full | ✅ Full | ❓ | ⚠️ Start/Stop only | ⚠️ Start/Stop only |
| Step Functions | ✅ Full | ✅ Full | ❓ | ⚠️ Start/Stop only | ⚠️ Start/Stop only |
| **Infrastructure** |
| CloudFormation | ✅ Full | ✅ Full | ❓ | ❌ Read-only | ✅ Full |
| VPC/Subnets | ❌ Denied | ✅ Full | ❓ | ❌ Read-only | ❌ Read-only |
| Security Groups | ❌ Denied | ✅ Full | ❓ | ❌ Read-only | ❌ Read-only |
| Load Balancers | ❌ Denied | ✅ Full | ❓ | ❌ Read-only | ❌ Read-only |
| **IAM** |
| IAM roles | ❌ Denied | ✅ With boundary | ❓ | ❌ Read-only | ✅ With boundary |
| IAM users | ❌ Denied (global) | ❌ Denied (global) | ❌ Denied | ❌ Denied | ❌ Denied |
| **Messaging** |
| SQS | ✅ Full | ✅ Full | ❓ | ✅ Full | ✅ Full |
| SNS | ✅ Full | ✅ Full | ❓ | ⚠️ Topic CRUD only | ⚠️ Topic CRUD only |
| EventBridge | ✅ Full | ✅ Full | ❓ | ❌ Read-only | ✅ Full |
| **Secrets** |
| Secrets Manager | ❌ List/Describe only | ✅ Full | ❓ | ✅ Read + Update | ✅ Read + Update |

---

## Recommended Next Steps

### Immediate (This Week):
1. ✅ Document account-based approach (this file)
2. ⚠️ Decide on staging account classification (209479269442)
3. ⚠️ Classify unassigned accounts (Digital Tools Prod, Pharmacy Prod, etc.)
4. ⚠️ Consider adding RDS to all dev/qa accounts (not just 2)
5. ⚠️ Consider adding basic ECS ops to MH-Engineer prod (UpdateService, RunTask, StopTask)

### Short-term (Next Month):
1. Test with Micah & Keith across all 13 accounts
2. Validate operational scenarios in each environment
3. Roll out to full Platform Data team after validation

### Long-term (3-6 Months):
1. Restructure accounts to align with environments (one per team per env)
2. Re-evaluate tag-based access control after account consolidation
3. Consider Service Control Policies (SCPs) for org-wide cost controls

---

## Files
- `stacks/02-mh-engineer.yaml` - Account-based permission set
- `stacks/03-mh-lead.yaml` - Account-based permission set (includes all Engineer perms + elevated)
- `ACCOUNT-ENVIRONMENT-MAPPING.md` - This file
