# Simple Permissions Guide - MH-Engineer vs MH-Lead

**Last Updated:** 2026-05-07 (After cleanup - removed 3 bad AWS-managed policies)

**TL;DR:**  
Sandbox/Dev = build freely  
Prod Engineer = operate safely  
Prod Lead = deploy through structure (CloudFormation-first)

---

## 🟢 SANDBOX (Account: 123185598779)

### MH-Engineer & MH-Lead (SAME in Sandbox)

**✅ CAN DO (Almost Everything):**
- Create/modify/delete EC2, RDS, Lambda, S3, DynamoDB, ECS, etc.
- Deploy Elastic Beanstalk applications
- Create security groups (not VPCs/subnets)
- Create IAM roles (with boundaries)
- Full CloudFormation
- Experiment freely

**❌ CANNOT DO:**
- AWS Marketplace purchases
- Create/modify VPCs, subnets, routing tables, NAT gateways
- Create IAM users or access keys
- Read secret values (can create/list secrets, just not read values)

---

## 🔵 DEV/QA (4 Accounts: data-dev, data-qa, pdt-dev, pdt-qa)

### MH-Engineer & MH-Lead (SAME in Dev/QA)

**✅ CAN DO (Full Write):**
- Create/modify/delete Lambda, S3, SQS, SNS, DynamoDB
- Create/modify/delete ECS, ECR, API Gateway
- Deploy CloudFormation stacks
- Create/modify RDS (only in data-dev and pdt-dev, NOT QA)
- Create IAM roles (with dev_boundary)
- Read AND write secrets
- Full CloudWatch, logs, X-Ray
- Start/stop Glue, Athena, DataBrew, Step Functions, Airflow

**❌ CANNOT DO:**
- Create/modify VPCs, subnets, routing
- Create IAM users
- Use expensive instance types (GPU, HPC)

---

## 🔴 PRODUCTION (5 Accounts: data-prod, pdt-prod, pdt-staging, pharmacy-prod, mh-ops)

### MH-Engineer (Operational Only)

**✅ CAN DO:**
- **Lambda:** Invoke functions (not create/modify)
- **S3:** Put/delete objects (not create/delete buckets)
- **DynamoDB:** Query/Scan/Get/Put/Update/Delete items (not create/delete tables)
- **SQS:** All queue operations (purge, send, receive, delete messages)
- **Data Jobs:** Start/stop Glue, Athena, DataBrew, Step Functions (not modify job definitions)
- **Logs:** Read CloudWatch logs, live tail
- **Secrets:** List/describe secrets (CANNOT read values - prevents credential exfiltration)
- **Cognito:** Manage resource servers
- **Airflow:** Full access

**❌ CANNOT DO:**
- Deploy or modify runtime code or task definitions (Lambda, ECS)
- Deploy CloudFormation
- Create any infrastructure (EC2, RDS, S3 buckets, DynamoDB tables)
- Read secret values
- Create/modify IAM roles
- Create inline IAM policies
- Modify API Gateway
- Create CloudWatch dashboards (centralized dashboards owned by platform team)

---

### MH-Lead (Operational + Deployment)

**✅ CAN DO (Everything Engineer Has PLUS):**
- **Lambda:** Create, update code, delete functions
- **CloudFormation:** Full stack management
- **API Gateway:** Create/modify/delete APIs
- **ECS/ECR:** Full deployment (push images, update task definitions, services)
- **EventBridge/Scheduler:** Create/modify rules
- **SSM Parameter Store:** Put/delete parameters
- **Secrets:** Read AND update secret values (for key rotation during deployments)
- **IAM:** Create roles with dev_boundary (only in data-prod and mh-ops, no inline policies)

**❌ CANNOT DO:**
- Create EC2 instances directly (must use CloudFormation)
- Create RDS databases directly (must use CloudFormation)
- Create S3 buckets directly (must use CloudFormation)
- Create inline IAM policies in prod
- Add Lambda function URLs (security risk - blocked)
- Remove permissions boundaries from IAM roles
- Create CloudWatch dashboards (centralized dashboards owned by platform team)

**Emergency Override:** Breakglass OrganizationAccountAccessRole exists for critical incidents (audited, time-bound)

---

## ⚪ READ-ONLY ACCOUNTS (3 Accounts: CostAnalytics, OurHealth-Dev, DevEx)

### All Roles (Engineer, Lead, Security)

**✅ CAN DO:**
- Read everything (describe, list, get)

**❌ CANNOT DO:**
- Modify anything

---

## Quick Comparison Table

| Permission | Sandbox | Dev/QA | Prod (Engineer) | Prod (Lead) |
|------------|---------|--------|-----------------|-------------|
| **Deploy Lambda** | ✅ Both | ✅ Both | ❌ Invoke only | ✅ Full |
| **Deploy CloudFormation** | ✅ Both | ✅ Both | ❌ Read only | ✅ Full |
| **Create S3 buckets** | ✅ Both | ✅ Both | ❌ No | ❌ No (use CFN) |
| **Put S3 objects** | ✅ Both | ✅ Both | ✅ Both | ✅ Both |
| **Delete S3 objects** | ✅ Both | ✅ Both | ✅ Both | ✅ Both |
| **Create DynamoDB tables** | ✅ Both | ✅ Both | ❌ No | ❌ No (use CFN) |
| **Write DynamoDB items** | ✅ Both | ✅ Both | ✅ Both | ✅ Both |
| **Read secrets** | ❌ No | ✅ Both | ❌ No | ✅ Yes |
| **Create IAM roles** | ✅ Both | ✅ Both | ❌ No | ✅ Limited |
| **Create EC2** | ✅ Both | ✅ Both | ❌ No | ❌ No (use CFN) |
| **Create RDS** | ✅ Both | ✅ Both (dev only) | ❌ No | ❌ No (use CFN) |

---

## Key Differences: Engineer vs Lead

### In Sandbox & Dev/QA:
**No difference** - Both have full access

### In Production:
**Engineer = Operational work** (run jobs, troubleshoot, fix data)  
**Lead = Deployment work** (deploy code, infrastructure, rotate secrets)

---

## What Both Roles CANNOT Do Anywhere (Guardrails)

These are blocked by the guardrails policy in ALL environments:

❌ Create IAM users or access keys  
❌ Remove permissions boundaries  
❌ Modify AWS Organizations  
❌ Disable CloudTrail, GuardDuty, Config, SecurityHub  
❌ Make snapshots public  
❌ Create VPN/Direct Connect/Transit Gateway  
❌ Use expensive instances (GPU, HPC, x1, x2)  
❌ Launch EMR, SageMaker tuning, or Redshift  
❌ Create unencrypted EBS volumes  
❌ Cross-account access outside the organization  

---

## Common Use Cases

### "I need to troubleshoot a prod issue"
→ Use **MH-Engineer**  
→ Can: Read logs, invoke Lambda, query DynamoDB, check SQS

### "I need to deploy code to prod"
→ Use **MH-Lead**  
→ Can: Update Lambda code, deploy CloudFormation, push ECS images

### "I need to experiment in sandbox"
→ Use **MH-Engineer** or **MH-Lead** (same access)  
→ Can: Create almost anything, test freely

### "I need to create infrastructure in prod"
→ Use **MH-Lead** + **CloudFormation**  
→ Cannot: Create resources directly (must use IaC)

---

## Who Should Have Which Role?

**MH-Engineer:**
- All engineers
- Daily operational work
- Troubleshooting prod issues
- Full dev/qa access

**MH-Lead:**
- Senior engineers
- DevOps/platform team
- People who deploy to prod
- Need to rotate secrets

**Assign sparingly:** Only give MH-Lead to people who actually deploy production code.

---

