# IAM Identity Center Roles - Permissions Summary

**Date**: 2026-05-06  
**Status**: Production Ready  
**Deployment**: All 3 roles deployed to all 13 AWS accounts

---

## Role Overview

| Role | Purpose | Target Users | Session Duration |
|------|---------|--------------|------------------|
| **MH-Security** | Security team access for incident response, compliance, and security tooling | Security team (1-2 people) | 8 hours |
| **MH-Engineer** | Base operational role for engineers | Platform Data, Digital Tools engineers (7-8 people) | 12 hours |
| **MH-Lead** | Elevated deployment role for leads | Tech leads, deployers (2-3 people) | 12 hours |

**Note**: MH-Lead is self-contained - includes everything MH-Engineer has plus elevated permissions. Users don't need both roles.

---

## MH-Security Permissions

### All Accounts
- ✅ **ViewOnlyAccess** (AWS managed policy)
- ✅ **SecurityAudit** (AWS managed policy)
- ✅ **Security Services**: GuardDuty, Security Hub, Inspector, Access Analyzer, Detective, Macie (full control)
- ✅ **Config**: Full remediation capabilities
- ✅ **Security Groups & NACLs**: Create, modify, delete
- ✅ **WAF/Shield**: Full management
- ✅ **CloudTrail**: Full management
- ✅ **VPC Flow Logs**: Create, delete, describe
- ✅ **KMS**: Key management (create, rotate, schedule deletion)
- ✅ **IAM**: Read-only + incident response (disable access keys, delete login profiles)
- ✅ **SSM Session Manager**: Forensics and incident response
- ✅ **CloudWatch Logs**: Query, filter, insights for forensics
- ✅ **S3 Security Logs**: Read CloudTrail/Config/GuardDuty buckets
- ✅ **SNS**: Create security alert topics
- ✅ **AWS Support**: Full access

### Blocked (Global Guardrails)
- ❌ IAM user creation
- ❌ Compute resource creation (EC2, RDS, Lambda)
- ❌ Application data modification

**Use Case**: Security team can investigate incidents, remediate security findings, manage security tooling, but cannot modify application infrastructure or data.

---

## MH-Engineer Permissions

### Sandbox Account (123185598779)
- ✅ `Action: "*"` (full access to experiment)
- ❌ **Blocked**: AWS Marketplace, VPC infrastructure, IAM users/policies, reading secret values

### Dev/QA Accounts (4 accounts)
**Accounts**: Platform Data Dev (201799325713), Platform Data QA (808468589041), Digital Tools Dev (686255955782), Digital Tools QA (593793032905)

- ✅ **Full Access**: Lambda, S3, DynamoDB, Glue, Athena, DataBrew, Step Functions, SQS, SNS, CloudWatch, Secrets Manager, EventBridge, API Gateway, Cognito, ECS, ECR, EC2, ELB, Auto Scaling, KMS, SSM, X-Ray, WAF, Airflow
- ✅ **CloudFormation**: Full deployment
- ✅ **IAM Roles**: Create/modify (requires `dev_boundary` permissions boundary)
- ✅ **RDS**: Full access in Platform Data Dev & Digital Tools Dev only (QA accounts do not have RDS)

### Staging/Prod Accounts (5 accounts)
**Accounts**: Platform Data Prod (971318514578), MH System Operations (266565038828), Digital Tools Staging (209479269442), Digital Tools Prod (476114142697), Pharmacy Prod (339712701706)

**Operational Access Only**:
- ✅ **Lambda**: Invoke (not create/update)
- ✅ **S3**: Put/delete objects, lifecycle configuration (not create buckets)
- ✅ **SQS**: All operations (purge queues, redrive DLQ)
- ✅ **DynamoDB**: All item operations (not table create/delete)
- ✅ **Glue/Athena/DataBrew/Step Functions**: Start/stop execution (not modify definitions)
- ✅ **Secrets Manager**: Read + update secret values
- ✅ **CloudWatch**: Create dashboards, filter logs, metrics
- ✅ **Cognito**: Resource server management
- ✅ **SNS**: Topic CRUD
- ✅ **Airflow**: Full access
- ✅ **IAM**: PassRole (limited to Lambda, DataBrew, Airflow, Scheduler services)
- ❌ **NO Access**: EC2, RDS, ECS, CloudFormation, Lambda CRUD, API Gateway

### ReadOnly Accounts (3 accounts)
**Accounts**: CostAnalytics (126693536052), OurHealth Dev (648300264365), DevEx (016592542065)

- ✅ **ReadOnlyAccess** only (AWS managed policy)
- ❌ No write permissions

---

## MH-Lead Permissions

**MH-Lead = MH-Engineer + Elevated Prod Deployment**

### Sandbox, Dev/QA, ReadOnly
- ✅ **Same as MH-Engineer** (full access in dev/qa, experiments in sandbox, read-only in 3 accounts)

### Staging/Prod Accounts (5 accounts)
**Everything MH-Engineer has PLUS**:

- ✅ **Lambda**: Full CRUD (create, update code, delete, publish versions, aliases, layers, concurrency)
- ✅ **CloudFormation**: Full deployment
- ✅ **API Gateway**: Full management
- ✅ **ECS/ECR**: Full deployment (task definitions, services, images)
- ✅ **EventBridge/Scheduler**: Full event routing
- ✅ **SSM Parameters**: Put/delete parameters
- ✅ **X-Ray**: Full tracing
- ✅ **IAM Roles**: Create/modify (requires `dev_boundary` permissions boundary)

**Still Blocked in Prod**:
- ❌ EC2 instance creation (CloudFormation can create them)
- ❌ RDS database creation (CloudFormation can create them)
- ❌ S3 bucket creation (CloudFormation can create them)
- ❌ VPC infrastructure (blocked by guardrails)

**Design Philosophy**: Infrastructure changes go through CloudFormation (audit trail). Application deployments (Lambda code, ECS tasks) can be done directly for speed.

---

## Global Guardrails (All 3 Roles)

Applied via `MH-Engineer-Guardrails` customer-managed policy in each account:

### Security Protections
- ❌ **IAM User Creation**: Cannot create IAM users, access keys, login profiles
- ❌ **Permissions Boundary**: Cannot remove or modify dev_boundary/data_engineer boundaries
- ❌ **Privilege Escalation**: Cannot modify MH-Engineer/MH-Lead/MH-Security CloudFormation stacks
- ❌ **SSO/Identity**: Cannot use sso-admin or identitystore APIs
- ❌ **PassRole**: Cannot pass OrganizationAccountAccessRole or SSO service roles
- ❌ **Organizations**: Cannot modify AWS Organizations or close accounts
- ❌ **Audit Tampering**: Cannot disable/delete CloudTrail, GuardDuty, Config, SecurityHub, Access Analyzer, Macie

### Cost Controls
- ❌ **Expensive Instances**: Cannot launch GPU (g4dn, g5, g6, p3, p4d, p5), ML (inf1, inf2, trn1, trn2), HPC (hpc6, hpc7), or large memory (x1, x2) instances
- ❌ **Expensive Services**: Cannot create EMR clusters, SageMaker hyperparameter tuning jobs, Redshift clusters
- ❌ **Unencrypted EBS**: All EBS volumes must be encrypted

### Data Protection
- ❌ **Data Exfiltration**: Cannot create S3 replication, modify snapshot sharing, export DynamoDB tables, or modify EFS policies
- ❌ **Network Egress**: Cannot create VPC peering, VPN, Transit Gateway, or Direct Connect
- ❌ **Cross-Org Assume**: Cannot assume roles outside organization o-vzuq8g0yfs

### Infrastructure Protection
- ❌ **Terraform State**: Cannot modify marathonhealth-terraform S3 bucket
- ❌ **Region Lock**: All operations limited to us-east-1 (except global services like IAM, Route53, CloudFront)

---

## Account Classifications

### Sandbox (1 account)
- 123185598779 - Platform Sandbox

### Dev/QA (4 accounts)
- 201799325713 - Platform Data Dev
- 808468589041 - Platform Data QA
- 686255955782 - Platform Digital Tools Dev
- 593793032905 - Platform Digital Tools QA

### Staging/Prod (5 accounts)
- 971318514578 - Platform Data Prod
- 266565038828 - MH System Operations (management account)
- 209479269442 - Platform Digital Tools Staging
- 476114142697 - Platform Digital Tools Prod
- 339712701706 - Pharmacy Prod

### ReadOnly (3 accounts)
- 126693536052 - CostAnalytics-DataCollection (dashboards)
- 648300264365 - OurHealth Dev (unused)
- 016592542065 - DevEx (Bedrock only)

---

## Permission Set Structure

### MH-Security
- **Managed Policies**: ViewOnlyAccess, SecurityAudit
- **Inline Policy**: ~6KB of security-specific permissions
- **Customer-Managed**: None
- **Tags**: mh:application=iam-identity-center, mh:environment=prod, mh:business-unit=cose

### MH-Engineer
- **Managed Policies**: ReadOnlyAccess
- **Inline Policy**: ~8KB of environment-specific allow statements
- **Customer-Managed**: MH-Engineer-Guardrails (deny statements)
- **Tags**: None

### MH-Lead
- **Managed Policies**: ReadOnlyAccess
- **Inline Policy**: ~9KB of environment-specific allow statements (includes all MH-Engineer + prod deployment)
- **Customer-Managed**: MH-Engineer-Guardrails (deny statements)
- **Tags**: None

---

## Test Phase

**Status**: TEST PHASE - Limited to Micah Burkhardt & Keith Ferguson

**Entra ID Groups**:
- `AWS-MH-Engineer`: Micah, Keith, +1 other
- `AWS-MH-Lead`: Micah, Keith

**Testing Period**: 3-4 weeks (through ~June 2026)

**Success Criteria**:
- Engineers can perform operational tasks in prod without access denied errors
- Leads can deploy infrastructure changes in staging/prod
- Guardrails effectively block risky operations
- No privilege escalation possible

**Rollout Plan**: After successful testing, expand to full Platform Data team (7-8 engineers, 2-3 leads)

---

## Key Differences from Current Roles

### vs. CloudPlatformEngineer (being replaced)
- ✅ **Better**: Org-wide (not account-specific), consistent permissions, stronger guardrails
- ✅ **Better**: Two-tier model (Engineer vs Lead) for least privilege
- ⚠️ **Different**: Prod access is operational-only for Engineers (not full deployment)

### vs. Administrator (not replaced)
- ❌ **Less**: Administrators still have unrestricted access (no guardrails)
- ✅ **Safer**: MH-Engineer/MH-Lead cannot escalate privileges, modify audit tools, or launch expensive resources

---

## Recommended Review Points

1. **Prod Operational Access**: Is the MH-Engineer prod permission set sufficient for incident response? May need to add ECS restart capabilities.

2. **RDS in QA**: QA accounts don't have RDS access. Is this intentional or should QA be able to create test databases?

3. **CloudFormation in Prod**: MH-Lead can deploy any CloudFormation template to prod. Should there be additional controls (approval workflow, PR requirement)?

4. **Cost Controls**: Guardrails block expensive instance types but not expensive instance counts. Consider AWS Budgets alerts.

5. **Sandbox VPC Restrictions**: Sandbox users cannot create VPCs/subnets. Is this too restrictive for experimentation?

---

## Questions for Architect

1. Should staging be treated more like dev (full write) or prod (operational only)? Currently: Prod-like.

2. Do we want Service Control Policies (SCPs) at org level for cost/security controls instead of per-role guardrails?

3. Is the two-tier model (Engineer vs Lead) sufficient, or do we need additional tiers?

4. Should ReadOnly accounts (CostAnalytics, OurHealth Dev, DevEx) be removed from role assignments entirely?

5. Long-term: Move to tag-based access control once accounts are restructured to align with environments?

