# MH-Engineer & MH-Lead Deployment Guide

**Status**: 🟡 TEST PHASE - Micah & Keith only  
**Created**: May 6, 2026  
**Model**: Org-wide roles with tag-based access control

---

## Overview

Two new **org-wide** permission sets for engineering/data platform work:

- **MH-Engineer** (Base): Operational access for standard engineers
- **MH-Lead** (Elevated): Adds infrastructure deployment for leads/deployers

**Access Model**: Tag-based (not account-specific)
- Assigned to **all 13 accounts**
- Permissions adjust based on `mh:environment` tag
- Sandbox account gets full access

**Current Phase**: Testing with Micah Burkhardt & Keith Ferguson only

---

## What These Roles Do

### MH-Engineer (Base Role)

**Sandbox Account (123185598779)**:
- Full `Action: "*"` (experiment freely)
- Still blocked by guardrails (no IAM users, no Orgs, no audit tampering)

**Dev/QA/Stage (tagged `mh:environment: dev|qa|stage`)**:
- Full write: Lambda, CloudFormation, S3, Glue, Athena, DynamoDB, SQS, SNS, etc.
- IAM role creation (with boundary required)
- ECS, ECR, API Gateway, Step Functions, EventBridge, etc.

**Prod (tagged `mh:environment: prod|production`)**:
- Operational: S3 put/delete, DynamoDB item ops, SQS all ops, Lambda invoke
- Glue/Athena/DataBrew/Step Functions start/stop (not modify definitions)
- ECS UpdateService, RunTask, StopTask
- Secrets Manager read (not update)
- CloudWatch dashboards, logs
- Read everything else

**Blocked Everywhere**:
- EC2/RDS/VPC creation
- Security group changes
- Networking (VPC peering, TGW, VPN) - blocked by guardrails
- Expensive instances - blocked by guardrails
- Audit service tampering - blocked by guardrails

---

### MH-Lead (Elevated - Additive)

**Additional access in Prod** (on top of MH-Engineer):
- Lambda CRUD (create, update code, delete)
- CloudFormation full
- API Gateway full
- ECS full
- ECR full
- EventBridge full
- IAM role creation (with boundary)

**Users get BOTH roles assigned** (Base + Ops = full access)

---

## Guardrails (Applied to Both)

Customer-managed policy: `MH-Engineer-Guardrails`

**Blocks**:
- IAM user creation
- Remove permissions boundaries
- AWS Organizations changes
- CloudTrail/GuardDuty/Config/SecurityHub disable
- VPC Peering, Transit Gateway, VPN, Direct Connect
- Expensive instances (GPU, ML, HPC)
- Reserved Instance purchases
- Cross-account AssumeRole (outside org)
- Public S3 ACLs
- Unencrypted EBS volumes

**Region lock**: us-east-1 only

---

## Deployment Steps

### Phase 1: Create Customer-Managed Policy (Guardrails)

**This must be done in EACH account** (all 13 accounts):

```bash
ACCOUNTS=(
  "476114142697"  # Platform Digital Tools Prod
  "971318514578"  # Platform Data Prod
  "339712701706"  # Pharmacy Prod
  "266565038828"  # MH System Operations
  "126693536052"  # CostAnalytics-DataCollection
  "209479269442"  # Platform Digital Tools Staging
  "593793032905"  # Platform Digital Tools QA
  "686255955782"  # Platform Digital Tools Dev
  "808468589041"  # Platform Data QA
  "201799325713"  # Platform Data Dev
  "123185598779"  # Platform Sandbox
  "648300264365"  # OurHealth Dev
  "016592542065"  # DevEx
)

for account in "${ACCOUNTS[@]}"; do
  echo "Creating guardrails policy in account $account"
  
  aws iam create-policy \
    --policy-name MH-Engineer-Guardrails \
    --policy-document file://policies/mh-engineer-guardrails.json \
    --description "Guardrails for MH-Engineer and MH-Lead permission sets - org-wide" \
    --profile mh-ops \
    --region us-east-1 \
    || echo "  Policy may already exist in $account"
done
```

**Verify**:
```bash
aws iam get-policy \
  --policy-arn arn:aws:iam::201799325713:policy/MH-Engineer-Guardrails \
  --profile mh-ops
```

---

### Phase 2: Deploy MH-Engineer Permission Set

```bash
aws cloudformation create-stack \
  --stack-name MH-Engineer-PermissionSet \
  --template-body file://stacks/02-mh-engineer.yaml \
  --parameters ParameterKey=DryRun,ParameterValue=false \
  --profile mh-ops \
  --region us-east-1 \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name MH-Engineer-PermissionSet \
  --profile mh-ops \
  --region us-east-1
```

**Verify**:
```bash
aws sso-admin list-permission-sets \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --profile mh-ops \
  --region us-east-1 \
  | grep MH-Engineer
```

---

### Phase 3: Deploy MH-Lead Permission Set

```bash
aws cloudformation create-stack \
  --stack-name MH-Lead-PermissionSet \
  --template-body file://stacks/03-mh-lead.yaml \
  --parameters ParameterKey=DryRun,ParameterValue=false \
  --profile mh-ops \
  --region us-east-1 \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name MH-Lead-PermissionSet \
  --profile mh-ops \
  --region us-east-1
```

---

### Phase 4: Assign to Test Users (Micah & Keith)

**Create Entra ID Test Group** (if doesn't exist):
- Group: `AWS MH-Engineer Test`
- Members: Micah Burkhardt, Keith Ferguson

**Assign MH-Engineer to ALL 13 accounts**:
```bash
PERMISSION_SET_ARN=$(aws sso-admin list-permission-sets \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --profile mh-ops \
  --region us-east-1 \
  --query "PermissionSets[?contains(@, 'MH-Engineer')]" \
  --output text)

GROUP_ID="<entra-group-id-for-test-group>"

ACCOUNTS=(
  "476114142697" "971318514578" "339712701706" "266565038828" "126693536052"
  "209479269442" "593793032905" "686255955782" "808468589041" "201799325713"
  "123185598779" "648300264365" "016592542065"
)

for account in "${ACCOUNTS[@]}"; do
  aws sso-admin create-account-assignment \
    --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
    --target-id $account \
    --target-type AWS_ACCOUNT \
    --permission-set-arn $PERMISSION_SET_ARN \
    --principal-type GROUP \
    --principal-id $GROUP_ID \
    --profile mh-ops \
    --region us-east-1
done
```

**Assign MH-Lead to ALL 13 accounts** (additive on top of MH-Engineer):
```bash
LEAD_PS_ARN=$(aws sso-admin list-permission-sets \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --profile mh-ops \
  --region us-east-1 \
  --query "PermissionSets[?contains(@, 'MH-Lead')]" \
  --output text)

# Same accounts - permissions adjust based on tags
for account in "${ACCOUNTS[@]}"; do
  aws sso-admin create-account-assignment \
    --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
    --target-id $account \
    --target-type AWS_ACCOUNT \
    --permission-set-arn $LEAD_PS_ARN \
    --principal-type GROUP \
    --principal-id $GROUP_ID \
    --profile mh-ops \
    --region us-east-1
done
```

---

## Testing Checklist

### Week 1: Sandbox/Dev Testing (Micah & Keith)

**Platform Data Dev (201799325713)**:
- [ ] Create Lambda function
- [ ] Create Glue job
- [ ] Upload file to S3
- [ ] Create DynamoDB table
- [ ] Create SQS queue
- [ ] Deploy via CloudFormation
- [ ] Create IAM role (with boundary)

**Platform Data Prod (971318514578)** - MH-Engineer only:
- [ ] Read Lambda function
- [ ] Invoke Lambda function ✓ (allowed)
- [ ] Try to update Lambda code ✗ (should be denied - need MH-Lead)
- [ ] Upload file to S3 ✓ (allowed)
- [ ] Delete file from S3 ✓ (allowed)
- [ ] Update DynamoDB item ✓ (allowed)
- [ ] Purge SQS queue ✓ (allowed)
- [ ] Try to create EC2 instance ✗ (should be denied)
- [ ] Try to modify security group ✗ (should be denied)

**Platform Data Prod (971318514578)** - MH-Lead:
- [ ] Update Lambda code ✓ (allowed with Lead)
- [ ] Deploy CloudFormation ✓ (allowed with Lead)
- [ ] Create API Gateway ✓ (allowed with Lead)

---

### Week 2: Guardrails Testing

**Verify blocks work**:
- [ ] Try to create IAM user ✗ (guardrails block)
- [ ] Try to disable CloudTrail ✗ (guardrails block)
- [ ] Try VPC peering ✗ (guardrails block)
- [ ] Try to create GPU instance ✗ (guardrails block)
- [ ] Try cross-region action ✗ (us-east-1 lock)

---

### Week 3-4: Production Validation

**Real incident simulation**:
- [ ] Drop eligibility file to trigger pipeline
- [ ] Purge DLQ and redrive messages
- [ ] Fix corrupted DynamoDB state
- [ ] Manually invoke failed Lambda
- [ ] Create CloudWatch dashboard for monitoring

**Success Criteria**: All operational scenarios work without access denied errors

---

## Rollout to Platform Data Team

**After 3-4 weeks of testing with Micah & Keith**:

1. Create production Entra groups:
   - `AWS MH-Engineer` (7-8 people)
   - `AWS MH-Lead` (2-3 people)

2. Assign groups to permission sets

3. Monitor for 2 weeks

4. Remove old CloudPlatformEngineer roles (if replacing)

---

## Rollback Procedure

**If issues found during testing**:

```bash
# Remove assignments
aws sso-admin delete-account-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --target-id <account-id> \
  --target-type AWS_ACCOUNT \
  --permission-set-arn <ps-arn> \
  --principal-type GROUP \
  --principal-id <group-id> \
  --profile mh-ops \
  --region us-east-1

# Delete stacks
aws cloudformation delete-stack \
  --stack-name MH-Lead-PermissionSet \
  --profile mh-ops \
  --region us-east-1

aws cloudformation delete-stack \
  --stack-name MH-Engineer-PermissionSet \
  --profile mh-ops \
  --region us-east-1

# Delete guardrails policies from each account
for account in "${ACCOUNTS[@]}"; do
  aws iam delete-policy \
    --policy-arn arn:aws:iam::$account:policy/MH-Engineer-Guardrails \
    --profile mh-ops-$account
done
```

---

## Summary

✅ **Ready to deploy**: CloudFormation stacks + guardrails policies created  
🟡 **TEST PHASE**: Micah & Keith only for 3-4 weeks  
📋 **Next**: After validation, roll out to Platform Data team  

**Files**:
- `policies/mh-engineer-base.json` - Base role policy
- `policies/mh-engineer-guardrails.json` - Guardrails deny policy
- `policies/mh-lead-ops-delta.json` - Lead additive policy
- `stacks/02-mh-engineer.yaml` - CloudFormation for MH-Engineer
- `stacks/03-mh-lead.yaml` - CloudFormation for MH-Lead
