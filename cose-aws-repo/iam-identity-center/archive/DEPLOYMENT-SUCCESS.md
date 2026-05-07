# MH-Engineer & MH-Lead Deployment - SUCCESS

**Date**: 2026-05-06  
**Deployed By**: Micah Burkhardt  
**Status**: ✅ DEPLOYED - Ready for assignment

---

## Deployment Summary

Successfully deployed two new org-wide permission sets to IAM Identity Center:

### MH-Engineer (Base Role)
- **Permission Set ARN**: `arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223e550ce22c566`
- **CloudFormation Stack**: `MH-Engineer-PermissionSet` (CREATE_COMPLETE)
- **Session Duration**: 12 hours
- **Description**: Base role for data platform engineers - operational access

### MH-Lead (Elevated Role)
- **Permission Set ARN**: `arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223f99c07c1a588`
- **CloudFormation Stack**: `MH-Lead-PermissionSet` (CREATE_COMPLETE)
- **Session Duration**: 12 hours
- **Description**: Elevated role for deployers/leads - adds infrastructure deployment

---

## What Was Deployed

### Permission Structure
- **MH-Engineer**: Full access in dev/qa/stage, operational access in prod, full access in sandbox
- **MH-Lead**: Adds prod infrastructure deployment capabilities on top of MH-Engineer
- **Guardrails**: Inline deny policies block risky actions (IAM users, audit tampering, expensive resources)

### Access Model
- **Tag-based**: Uses `mh:environment` tags to adjust permissions dynamically
- **Org-wide**: Will work across all 13 AWS accounts
- **Additive**: Users get both MH-Engineer + MH-Lead for full elevated access

### Guardrails Applied
- ❌ IAM user creation
- ❌ Permissions boundary removal/modification
- ❌ AWS Organizations changes
- ❌ Audit service tampering (CloudTrail, GuardDuty, etc.)
- ❌ Data exfiltration mechanisms
- ❌ VPC peering, VPN, Direct Connect
- ❌ Expensive instances (GPU, HPC, ML)
- ❌ Cross-account AssumeRole (outside org o-vzuq8g0yfs)
- ❌ Unencrypted EBS volumes
- ✅ Region-locked to us-east-1

---

## Next Steps

### 1. Create Test Entra ID Group
Create group in Entra ID:
- **Name**: `AWS MH-Engineer Test`
- **Members**: Micah Burkhardt, Keith Ferguson

### 2. Get Group ID
```bash
# Find the group in Identity Store
aws identitystore list-groups \
  --identity-store-id d-9067bf27c1 \
  --profile mh-ops \
  --region us-east-1 \
  --filters AttributePath=DisplayName,AttributeValue="AWS MH-Engineer Test"
```

### 3. Assign to All 13 Accounts
Using the Python script:
```bash
# Assign MH-Engineer
python scripts/assign-permission-set.py \
  --permission-set MH-Engineer \
  --group "AWS MH-Engineer Test" \
  --all-accounts

# Assign MH-Lead (additive)
python scripts/assign-permission-set.py \
  --permission-set MH-Lead \
  --group "AWS MH-Engineer Test" \
  --all-accounts
```

### 4. Testing Phase (3-4 weeks)
Follow checklist in `MH-ENGINEER-LEAD-DEPLOYMENT.md`:
- Week 1: Sandbox/Dev testing
- Week 2: Guardrails validation
- Week 3-4: Production operational scenarios

### 5. Rollout to Full Teams
After successful testing:
- Create production Entra groups: `AWS MH-Engineer` and `AWS MH-Lead`
- Assign to full Platform Data team (7-8 engineers for base, 2-3 for lead)
- Monitor for 2 weeks
- Consider decommissioning old roles

---

## Verification Commands

### Check Permission Sets
```bash
# List all permission sets
aws sso-admin list-permission-sets \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --profile mh-ops \
  --region us-east-1

# Describe MH-Engineer
aws sso-admin describe-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223e550ce22c566 \
  --profile mh-ops \
  --region us-east-1

# Describe MH-Lead
aws sso-admin describe-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223f99c07c1a588 \
  --profile mh-ops \
  --region us-east-1
```

### Check CloudFormation Stacks
```bash
aws cloudformation describe-stacks \
  --stack-name MH-Engineer-PermissionSet \
  --profile mh-ops \
  --region us-east-1

aws cloudformation describe-stacks \
  --stack-name MH-Lead-PermissionSet \
  --profile mh-ops \
  --region us-east-1
```

---

## Rollback Procedure (If Needed)

```bash
# Remove assignments first (if any)
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
```

---

## Files in Repository

- `stacks/02-mh-engineer.yaml` - MH-Engineer CloudFormation template
- `stacks/03-mh-lead.yaml` - MH-Lead CloudFormation template
- `MH-ENGINEER-LEAD-DEPLOYMENT.md` - Complete deployment guide
- `scripts/assign-permission-set.py` - Assignment automation script
- `DEPLOYMENT-SUCCESS.md` - This file

---

## Target Accounts (All 13)

1. 476114142697 - Platform Digital Tools Prod
2. 971318514578 - Platform Data Prod
3. 339712701706 - Pharmacy Prod
4. 266565038828 - MH System Operations (Management)
5. 126693536052 - CostAnalytics-DataCollection
6. 209479269442 - Platform Digital Tools Staging
7. 593793032905 - Platform Digital Tools QA
8. 686255955782 - Platform Digital Tools Dev
9. 808468589041 - Platform Data QA
10. 201799325713 - Platform Data Dev
11. 123185598779 - Platform Sandbox
12. 648300264365 - OurHealth Dev
13. 016592542065 - DevEx

---

## Success Criteria

✅ CloudFormation stacks deployed successfully  
✅ Permission sets visible in IAM Identity Center  
✅ Templates validated  
✅ Guardrails inline (no external dependencies)  
✅ Consistent with MH-Security pattern  
⏳ Pending: Entra ID group creation  
⏳ Pending: Assignment to test users  
⏳ Pending: 3-4 week testing phase  

**Status**: Ready for Phase 3 (Assignments)
