# Production Access Review - Are We Giving Too Much?

**Date:** 2026-05-07  
**Status:** POST-CLEANUP (removed 3 bad AWS-managed policies)  
**Production Accounts:** data-prod, mh-ops, pdt-staging, pdt-prod, pharmacy-prod

---

## Quick Answer: No, Access is Appropriate ✅

After removing the 3 policies Awad added, prod access is scoped correctly for operational work and deployments.

---

## MH-Engineer in Production (Operational Access)

### ✅ What They CAN Do (Appropriate)

**Data Operations:**
- Run existing Lambda functions (invoke only, not modify)
- Put/delete objects in S3 (not create/delete buckets)
- Query/update DynamoDB items (not create/delete tables)
- Purge/redrive SQS queues
- Start/stop data jobs (Glue, Athena, DataBrew, Step Functions)

**Monitoring:**
- Read CloudWatch logs (live tail, filter)
- View secret metadata (NOT read values)

**Why this is appropriate:** Engineers need to troubleshoot prod issues, restart services, clear queues, fix data processing issues.

### ❌ What They CANNOT Do (Blocked)

- Create/modify Lambda functions
- Create/delete S3 buckets
- Create/delete DynamoDB tables
- Read secret values
- Deploy CloudFormation
- Create EC2, RDS, ECS resources
- Modify IAM roles
- Create CloudWatch dashboards

**Why blocked:** These are infrastructure changes requiring Lead approval/deployment.

---

## MH-Lead in Production (Operational + Deployment)

### ✅ What They CAN Do (Appropriate)

**Everything MH-Engineer can do PLUS:**

**Deployment:**
- Deploy Lambda functions (create, update code, delete)
- Deploy CloudFormation stacks
- Deploy ECS services (task definitions, services, images)
- Deploy API Gateway changes
- Manage EventBridge/Scheduler rules
- Update SSM Parameter Store values
- **Read AND update secrets** (for key rotation during deploys)

**IAM (LIMITED):**
- Create IAM roles **only with `dev_boundary` permissions boundary**
- Only in data-prod and mh-ops accounts

**Why this is appropriate:** Leads need to deploy application code and infrastructure to prod.

### ❌ What They CANNOT Do (Blocked)

- Create EC2 instances directly (must use CloudFormation)
- Create RDS databases directly (must use CloudFormation)
- Create S3 buckets directly (must use CloudFormation)
- Add Lambda function URLs (blocked - security risk)
- Add Lambda layer permissions publicly (blocked - security risk)
- Modify CloudFormation stack types (blocked - org-level risk)
- Remove permissions boundaries from IAM roles (blocked by guardrails)
- Create IAM users or access keys (blocked by guardrails)

**Why blocked:** These are higher-risk actions requiring manual review or org-level approval.

---

## Specific Prod Risks - Mitigated ✅

### Risk 1: "Can they delete prod data?"

**MH-Engineer:**
- ✅ Can delete S3 objects (might be needed to fix data issues)
- ✅ Can delete DynamoDB items (might be needed for GDPR requests)
- ❌ Cannot delete S3 buckets
- ❌ Cannot delete DynamoDB tables

**MH-Lead:**
- Same as MH-Engineer (no additional delete permissions)

**Mitigation:**
- S3 versioning should be enabled (can recover deleted objects)
- DynamoDB point-in-time recovery should be enabled (can restore)
- CloudTrail logs all deletions (audit trail)

**Verdict:** Acceptable risk - engineers need ability to fix data issues

---

### Risk 2: "Can they deploy malicious code to prod Lambda?"

**MH-Engineer:**
- ❌ NO - Cannot modify Lambda code (invoke only)

**MH-Lead:**
- ✅ YES - Can update Lambda function code

**Mitigation:**
- Code should go through CI/CD pipeline with code review
- CloudTrail logs all Lambda updates (who deployed what)
- Lambda versions/aliases for rollback
- Organizational culture: Don't give MH-Lead to junior engineers

**Verdict:** Acceptable risk - deployers need this access, mitigate with process

---

### Risk 3: "Can they read prod secrets (DB passwords, API keys)?"

**MH-Engineer:**
- ❌ NO - Can only list/describe secrets, cannot read values

**MH-Lead:**
- ✅ YES - Can read AND update secret values

**Mitigation:**
- Secrets Manager logs all reads (CloudTrail)
- Only give MH-Lead to trusted deployers
- Rotate secrets regularly
- Use IAM database authentication where possible (no secrets)

**Verdict:** Acceptable risk - deployers need this for key rotation, migrations

---

### Risk 4: "Can they create IAM roles and escalate privileges?"

**MH-Engineer:**
- ❌ NO - Cannot create IAM roles in prod

**MH-Lead:**
- ⚠️ LIMITED - Can create IAM roles **only with `dev_boundary` permissions boundary**
- Only in data-prod (971318514578) and mh-ops (266565038828)

**What is `dev_boundary`?**
- A permissions boundary policy that limits what the created role can do
- Even if MH-Lead creates a role, that role is constrained by the boundary

**Mitigation:**
- Guardrails policy blocks removing permissions boundaries
- Guardrails policy blocks modifying the `dev_boundary` policy itself
- CloudTrail logs all IAM role creation

**Verdict:** Low risk - properly constrained with boundaries

---

### Risk 5: "Can they disable audit logging or security services?"

**Both MH-Engineer and MH-Lead:**
- ❌ NO - Blocked by guardrails policy

**Blocked actions:**
- Delete/stop CloudTrail
- Disable GuardDuty
- Disable SecurityHub
- Delete Config rules
- Disable Macie

**Verdict:** No risk - properly protected

---

## Comparison to Industry Standards

| Access Pattern | Your Setup | Typical Enterprise | Assessment |
|---------------|------------|-------------------|------------|
| **Engineers read prod** | ✅ Yes (logs, metrics, describe) | ✅ Standard | ✅ Appropriate |
| **Engineers write prod data** | ✅ Yes (S3 objects, DDB items) | ⚠️ Varies | ✅ Appropriate for data platform |
| **Engineers deploy prod code** | ❌ No (Lead only) | ✅ Standard | ✅ Good separation |
| **Deployers read secrets** | ✅ Yes (Lead only) | ✅ Standard | ✅ Appropriate |
| **Deployers create IAM roles** | ⚠️ Limited (with boundary) | ⚠️ Varies | ✅ Well-constrained |
| **Engineers modify networking** | ❌ No | ❌ Rare | ✅ Good restriction |

---

## Where You're More Restrictive Than Typical

1. **No EC2/RDS direct creation** - Must use CloudFormation
   - Pro: Infrastructure as code enforced
   - Con: Slower for experimentation (use sandbox for this)

2. **No CloudWatch dashboard creation** in prod
   - Pro: Prevents dashboard sprawl
   - Con: Can't quickly create dashboards during incidents
   - Workaround: Create in dev, export/import to prod via CloudFormation

3. **No Lambda function URLs** in prod
   - Pro: Prevents accidental public Lambda exposure
   - Con: Legitimate use case for webhooks
   - Workaround: Use API Gateway instead

---

## Where You're More Permissive Than Typical

1. **S3 object deletion** in prod (MH-Engineer)
   - Risk: Accidental data loss
   - Mitigation: S3 versioning + lifecycle policies + CloudTrail

2. **DynamoDB item writes** in prod (MH-Engineer)
   - Risk: Data corruption
   - Mitigation: Point-in-time recovery + CloudTrail

3. **Full Airflow access** in prod (both roles)
   - Risk: Modify DAGs, trigger expensive jobs
   - Mitigation: Airflow should have its own RBAC

---

## Recommended Tightening (Optional)

### Low-Hanging Fruit

1. **Remove S3 object deletion from MH-Engineer in prod**
   - Change to read-only S3 in prod for Engineer
   - Keep delete for Lead only
   - **Impact:** Engineers can't fix data issues without Lead

2. **Remove DynamoDB item writes from MH-Engineer in prod**
   - Change to read-only DynamoDB in prod for Engineer
   - Keep writes for Lead only
   - **Impact:** Engineers can't fix data issues without Lead

3. **Remove Airflow `*` access**
   - Scope to specific read-only actions
   - Let Airflow's own RBAC handle write permissions
   - **Impact:** Need to configure Airflow RBAC separately

### My Opinion: DON'T Tighten Yet

**Why:**
- You're in TEST phase (only Micah + Keith have these roles)
- Better to learn what's actually needed before restricting
- If you tighten too much, people will request overly-broad emergency access

**Better approach:**
- Monitor CloudTrail for 2-4 weeks
- See what actions are actually used
- Tighten based on real usage, not theoretical concerns

---

## Final Verdict: ✅ Access is Appropriate

**Summary:**
- MH-Engineer: Operational access (read + limited writes for troubleshooting)
- MH-Lead: Deployment access (infrastructure changes, secret rotation)
- Both: Properly blocked from privilege escalation, audit tampering, expensive resources

**Not giving too much access in prod.** The design is solid:
- Principle of least privilege ✅
- Separation of duties (Engineer vs Lead) ✅
- Defense in depth (guardrails policy) ✅
- Audit trail (CloudTrail) ✅

**Recommendation:** Keep as-is during test phase, monitor usage, adjust based on real patterns.

---

