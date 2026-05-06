# IAM Identity Center Roles - Permission Summary

**Date**: 2026-05-06  
**Status**: Production Ready  
**Deployment**: All 13 AWS accounts

---

## Three New Roles

### MH-Engineer (Base Engineering Role)
**Purpose**: Operational access for all engineers  
**Session**: 12 hours  
**Managed Policies**: ReadOnlyAccess

### MH-Lead (Elevated Engineering Role)  
**Purpose**: Infrastructure deployment for leads/deployers  
**Session**: 12 hours  
**Managed Policies**: ReadOnlyAccess  
**Note**: Self-contained (includes all MH-Engineer permissions + elevated)

### MH-Security (Security Team Role)
**Purpose**: Security team access for incident response and audit  
**Session**: 8 hours  
**Managed Policies**: ViewOnlyAccess, SecurityAudit

---

## Permission Breakdown by Environment

### 🟢 Sandbox (123185598779)

**MH-Engineer & MH-Lead**:
- ✅ Full `Action: "*"` access (experiment freely)
- ❌ Blocked: Marketplace, VPC infrastructure, IAM users/policies, reading secret values

**MH-Security**:
- ✅ Full security services (GuardDuty, SecurityHub, Inspector, Macie, etc.)
- ✅ Security group & NACL management
- ✅ WAF management
- ✅ CloudTrail, Config, VPC Flow Logs
- ✅ KMS key management
- ✅ IAM security audit (view only)
- ✅ IAM incident response (disable user access keys)

---

### 🔵 Dev/QA Accounts (4 accounts)
- 201799325713 - Platform Data Dev
- 808468589041 - Platform Data QA  
- 686255955782 - Platform Digital Tools Dev
- 593793032905 - Platform Digital Tools QA

**MH-Engineer & MH-Lead**:
- ✅ **Compute**: EC2, ECS, Lambda, Auto Scaling (full CRUD)
- ✅ **Storage**: S3, DynamoDB, RDS (Data Dev & Digital Tools Dev only)
- ✅ **Networking**: Security groups, Load balancers (NOT VPC infrastructure)
- ✅ **Data**: Glue, Athena, DataBrew, Step Functions
- ✅ **Integration**: SQS, SNS, EventBridge, API Gateway
- ✅ **Deployment**: CloudFormation
- ✅ **IAM**: Create roles with `dev_boundary` permissions boundary
- ✅ **Secrets**: Secrets Manager full access
- ✅ **Monitoring**: CloudWatch, X-Ray
- ❌ **Blocked**: VPCs/subnets/routing, expensive instances (GPU/HPC)

**MH-Security**: Same as sandbox

---

### 🟡🔴 Staging & Production (5 accounts)
- 971318514578 - Platform Data Prod
- 266565038828 - MH System Operations
- 209479269442 - Platform Digital Tools Staging
- 476114142697 - Platform Digital Tools Prod  
- 339712701706 - Pharmacy Prod

**MH-Engineer (Operational Only)**:
- ✅ **Lambda**: Invoke only (not create/update)
- ✅ **S3**: Put/delete objects (not buckets)
- ✅ **DynamoDB**: Item operations only (Query, Scan, Get, Put, Update, Delete, BatchGet, BatchWrite - NOT table CRUD)
- ✅ **SQS**: All operations (purge, redrive DLQ)
- ✅ **Data Jobs**: Start/stop only (Glue, Athena, DataBrew, Step Functions - NOT modify job definitions)
- ✅ **Secrets**: List and describe metadata ONLY (cannot read secret values)
- ✅ **Logs**: Search and live tail (not create dashboards or metric filters)
- ✅ **Cognito**: Resource server management
- ✅ **SNS**: Read topic attributes (cannot create/delete/modify)
- ❌ **NO**: Infrastructure creation, EC2, RDS, ECS, CloudFormation, secret values, CloudWatch dashboards

**MH-Lead (Operational + Deployment)**:
- ✅ **Everything MH-Engineer has PLUS:**
- ✅ **Secrets**: Can read secret values AND update (for key rotation during deployments)
- ✅ **Lambda**: Full CRUD (create, update code, delete)
- ✅ **CloudFormation**: Full stack management
- ✅ **API Gateway**: Full management
- ✅ **ECS/ECR**: Full deployment (task definitions, services, images)
- ✅ **EventBridge/Scheduler**: Full management
- ✅ **IAM**: Create roles with `dev_boundary` permissions boundary
- ❌ **NO**: Direct EC2 creation, RDS creation, S3 bucket creation (use CloudFormation), CloudWatch dashboards

**MH-Security**: Same as sandbox

---

### ⚪ ReadOnly Accounts (3 accounts)
- 126693536052 - CostAnalytics (dashboards)
- 648300264365 - OurHealth Dev (unused)
- 016592542065 - DevEx (Bedrock only)

**All Roles**: ReadOnlyAccess only (no write permissions)

---

## Guardrails (Applied to All Roles, All Accounts)

### Blocked Actions (Cannot Override):
- ❌ Create IAM users or access keys
- ❌ Remove or modify permissions boundaries (`dev_boundary`, `data_engineer`)
- ❌ Modify permission set CloudFormation stacks
- ❌ Use sso-admin or identitystore APIs
- ❌ Modify AWS Organizations or close accounts
- ❌ Disable audit services (CloudTrail, GuardDuty, Config, SecurityHub)
- ❌ Data exfiltration mechanisms (S3 replication, public access, snapshot sharing)
- ❌ VPC peering, VPN, Transit Gateway, Direct Connect
- ❌ Expensive instances: GPU (g4dn, g5, g6, p3, p4d, p5), HPC (hpc6, hpc7), Inference (inf1, inf2, trn1, trn2), Large memory (x1, x2)
- ❌ Expensive services: EMR, SageMaker hyperparameter tuning, Redshift
- ❌ Unencrypted EBS volumes
- ❌ Cross-account AssumeRole outside org (o-vzuq8g0yfs)
- ❌ Access to Terraform state bucket (marathonhealth-terraform)

### Region Lock:
- 🔒 All actions restricted to **us-east-1** only

---

## Key Differences Between Roles

| Capability | MH-Engineer | MH-Lead | MH-Security |
|------------|-------------|---------|-------------|
| **Dev/QA Full Write** | ✅ | ✅ | ❌ |
| **Prod Operational** | ✅ | ✅ | ❌ |
| **Prod Infrastructure Deployment** | ❌ | ✅ | ❌ |
| **CloudFormation in Prod** | ❌ Read | ✅ Full | ❌ Read |
| **Lambda CRUD in Prod** | ❌ Invoke only | ✅ Full | ❌ Read |
| **Security Services** | ❌ Read | ❌ Read | ✅ Full |
| **Security Group Management** | ✅ Dev/QA only | ✅ Dev/QA only | ✅ All accounts |
| **IAM Role Creation** | ✅ Dev/QA (with boundary) | ✅ Dev/QA & Prod (with boundary) | ❌ Read |
| **Incident Response** | ✅ Operational fixes | ✅ + Infrastructure fixes | ✅ Security-focused |

---

## Use Cases

### MH-Engineer
- Daily operational work in dev/qa
- Incident response in prod (restart services, query data, purge queues)
- Build and test in dev/qa environments
- Monitor production systems

### MH-Lead  
- Everything MH-Engineer can do PLUS:
- Deploy application code to production (Lambda, ECS)
- Deploy infrastructure via CloudFormation
- Manage API Gateway configurations
- Create/update IAM roles for services

### MH-Security
- Security incident investigation across all accounts
- Manage security controls (GuardDuty, SecurityHub, WAF)
- Respond to security events (disable compromised credentials)
- Modify security groups and network ACLs
- Configure CloudTrail and audit logging
- View all resources (no modification of application infrastructure)

---

## Access Model

**Assignment**: All roles assigned to all 13 accounts  
**Enforcement**: Account-based conditions (not tag-based)  
**Permissions**: Adjust automatically based on which account you access

**Example**: 
- User assumes MH-Engineer in Platform Data Dev → Gets full write access
- Same user assumes MH-Engineer in Platform Data Prod → Gets operational access only

---

## Deployment Status

✅ Both MH-Engineer and MH-Lead deployed and tested  
✅ MH-Security deployed (separate deployment)  
✅ Guardrails policy deployed to all 13 accounts  
✅ Security gap closed (privilege escalation protections active)  
🟡 TEST PHASE: Currently limited to Micah Burkhardt & Keith Ferguson  
📋 NEXT: 3-4 week validation, then roll out to Platform Data team

---

## Security Notes

1. **Privilege Escalation Protected**: Users cannot modify their own permission sets or assignments
2. **Permissions Boundaries Required**: All IAM role creation requires `dev_boundary` or `data_engineer` boundary
3. **Audit Trail**: All actions logged via CloudTrail
4. **Cost Controls**: Expensive compute blocked by guardrails
5. **Data Protection**: Exfiltration mechanisms blocked, encryption required
6. **Network Segmentation**: Cannot create network egress paths
