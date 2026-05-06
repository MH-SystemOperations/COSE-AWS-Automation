# Guardrails Refactor - TODO

**Status**: ⚠️ BLOCKED - Inline policy size limit exceeded  
**Date**: 2026-05-06  
**Blocker**: MH-Lead inline policy is 10,298 bytes (AWS limit: 10,240 bytes)

---

## Problem

When adding privilege escalation protections (deny SSO-admin, deny permission set stack modification, deny identitystore changes), the MH-Lead inline policy exceeded AWS's 10KB limit:

```
Current size of the non-whitespace characters present in the InlinePolicy Document is 10298 bytes 
which has exceeded the maximum limit of 10240 bytes
```

## Solution

Move all deny/guardrail statements from inline policies to a customer-managed policy:
1. Create `MH-Engineer-Guardrails` policy in each account
2. Remove deny statements from inline policies  
3. Reference the guardrails policy via `CustomerManagedPolicyReferences`

## Files Ready

✅ `policies/mh-engineer-guardrails-v2.json` - Complete guardrails policy with privilege escalation protections  
✅ `scripts/deploy-guardrails-policy.sh` - Deployment script for 10 accounts

## What Needs To Be Done

### Step 1: Deploy Guardrails Policy to Accounts

Run the deployment script:
```bash
cd iam-identity-center/scripts
chmod +x deploy-guardrails-policy.sh
./deploy-guardrails-policy.sh
```

This will create the `MH-Engineer-Guardrails` policy in:
- 123185598779 - Platform Sandbox
- 201799325713 - Platform Data Dev
- 808468589041 - Platform Data QA
- 686255955782 - Platform Digital Tools Dev
- 593793032905 - Platform Digital Tools QA
- 971318514578 - Platform Data Prod
- 266565038828 - MH System Operations
- 209479269442 - Platform Digital Tools Staging
- 476114142697 - Platform Digital Tools Prod
- 339712701706 - Pharmacy Prod

### Step 2: Update MH-Engineer Stack

Remove these sections from `stacks/02-mh-engineer.yaml` inline policy:
- DenyTerraformBucket
- DenyPermissionSetStackModification
- DenySSOAdminChanges
- DenyIdentityStoreChanges
- DenyIamUserCreation
- DenyBoundaryRemoval
- DenyBoundaryPolicyModification
- DenyAssumeRolePolicyUpdate
- DenyPassRoleToPrivilegedRoles
- DenyOrgAndAccountProtection
- DenyAuditServiceTampering
- DenyDataExfiltration
- DenyNetworkEgress
- DenyExpensiveInstances
- DenyExpensiveServices
- DenyUnencryptedEbs
- DenyCrossAccountAssumeRole

Add after the `InlinePolicy` section:
```yaml
      CustomerManagedPolicyReferences:
        - Name: MH-Engineer-Guardrails
          Path: /
```

### Step 3: Update MH-Lead Stack

Same as Step 2 - remove all deny statements and add `CustomerManagedPolicyReferences`.

Keep the sandbox-specific denies (SandboxDenyMarketplace, SandboxDenyVpcInfra, SandboxDenyIam, SandboxDenySecretValues) - those are context-specific, not general guardrails.

### Step 4: Deploy Updated Stacks

```bash
aws cloudformation update-stack \
  --stack-name MH-Engineer-PermissionSet \
  --template-body file://stacks/02-mh-engineer.yaml \
  --parameters ParameterKey=DryRun,ParameterValue=false \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile mh-ops \
  --region us-east-1

aws cloudformation update-stack \
  --stack-name MH-Lead-PermissionSet \
  --template-body file://stacks/03-mh-lead.yaml \
  --parameters ParameterKey=DryRun,ParameterValue=false \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile mh-ops \
  --region us-east-1
```

### Step 5: Verify

Test that:
- ✅ Engineers can still perform their normal operations
- ✅ Guardrails still block expensive instances, IAM users, etc.
- ✅ Privilege escalation protections work (can't modify permission set stacks)
- ✅ Can't use sso-admin or identitystore APIs

---

## Why This Happened

Initially chose inline policies for simplicity (consistent with MH-Security). But MH-Engineer and MH-Lead have:
- More allow statements (dev/qa/prod permissions)
- More deny statements (guardrails)
- Sandbox-specific denies
- Total exceeded 10KB limit when adding privilege escalation protections

## Current State (Deployed)

**MH-Engineer**: ✅ UPDATE_COMPLETE (has privilege escalation protections, under 10KB limit)  
**MH-Lead**: ❌ UPDATE_ROLLBACK_COMPLETE (failed due to size, rolled back to previous version without privilege escalation protections)

**Security Gap**: MH-Lead currently does NOT have:
- DenyPermissionSetStackModification
- DenySSOAdminChanges  
- DenyIdentityStoreChanges

Users with MH-Lead in the management account could theoretically modify their own permission set until this refactor is completed.

---

## Priority

🔴 **HIGH** - Complete this refactor to close the privilege escalation security gap.

