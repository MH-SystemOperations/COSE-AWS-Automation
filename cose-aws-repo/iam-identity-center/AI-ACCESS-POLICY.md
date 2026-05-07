# AI Services Access Policy

**Date:** 2026-05-07  
**Issue:** MH-Engineer/MH-Lead roles use AWS managed `ReadOnlyAccess` policy which:
1. Auto-updates without our control
2. Could include AI services in future
3. Gives broader read access than needed

---

## Current Problem

### DevEx Account (016592542065)
**Intended use:** Bedrock experimentation only  
**Current permission sets:** All 3 roles (MH-Engineer, MH-Lead, MH-Security) have `ReadOnlyAccess`  
**Risk:** Users can read ALL resources in DevEx, not just Bedrock

### AWS Managed Policy Risk
`ReadOnlyAccess` is maintained by AWS and updated frequently (last update: 2026-05-07).  
If AWS adds AI service read permissions, your roles automatically inherit them.

---

## Recommended Fix

### Option 1: Replace ReadOnlyAccess with Custom Policy (Recommended)

**Benefits:**
- ✅ Full control over what's included
- ✅ Explicit deny for AI services
- ✅ No surprise updates from AWS

**Implementation:**
1. Create custom read-only policy (see `mh-custom-readonly.json`)
2. Update MH-Engineer and MH-Lead to use custom policy instead of AWS managed
3. Add explicit deny for all AI services

**Effort:** 1 hour to update permission sets, test in sandbox

---

### Option 2: Add Explicit Deny for AI Services to Existing Roles

**Benefits:**
- ✅ Quick fix (no permission set redesign)
- ✅ Keeps current ReadOnlyAccess structure

**Implementation:**
Add to inline policy in MH-Engineer and MH-Lead:

```json
{
  "Sid": "DenyAllAIServices",
  "Effect": "Deny",
  "Action": [
    "bedrock:*",
    "sagemaker:*",
    "comprehend:*",
    "rekognition:*",
    "textract:*",
    "translate:*",
    "polly:*",
    "transcribe:*",
    "lex:*",
    "personalize:*",
    "forecast:*",
    "kendra:*",
    "augmentedai:*",
    "codewhisperer:*",
    "q:*"
  ],
  "Resource": "*"
}
```

**Effort:** 15 minutes to add statement, reprovision

---

### Option 3: Create Separate Bedrock-Only Permission Set for DevEx

**Benefits:**
- ✅ DevEx account truly isolated to Bedrock use
- ✅ Most secure option

**Implementation:**
Create `MH-Bedrock-User` permission set:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockFullAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock:CreateModelCustomizationJob",
        "bedrock:GetModelCustomizationJob",
        "bedrock:ListModelCustomizationJobs"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogsForBedrock",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:016592542065:log-group:/aws/bedrock/*"
    },
    {
      "Sid": "DenyAllOtherServices",
      "Effect": "Deny",
      "NotAction": [
        "bedrock:*",
        "logs:*",
        "sts:*",
        "sso:*"
      ],
      "Resource": "*"
    }
  ]
}
```

Assign `MH-Bedrock-User` to DevEx account only, remove MH-Engineer/MH-Lead from DevEx.

**Effort:** 2 hours (create new permission set, reassign users)

---

## Recommendation: Option 2 (Quick) + Option 1 (Long-term)

### This Week: Add Explicit AI Deny
```bash
# Add DenyAllAIServices statement to MH-Engineer and MH-Lead inline policies
# Reprovision to all accounts
# Test: Try to access Bedrock in any account → should be denied
```

### Next Month: Replace with Custom ReadOnly Policy
```bash
# Migrate away from AWS managed ReadOnlyAccess
# Use custom policy with only needed services
# Maintain AI deny block
```

---

## Testing Plan

### Test 1: Verify AI services blocked
```bash
# Login as MH-Engineer
aws bedrock list-foundation-models --region us-east-1
# Expected: AccessDenied

aws sagemaker list-models --region us-east-1
# Expected: AccessDenied
```

### Test 2: Verify core services still work
```bash
aws ec2 describe-instances --region us-east-1
# Expected: Success (or empty list)

aws s3 ls
# Expected: Success (list buckets)

aws lambda list-functions --region us-east-1
# Expected: Success (list functions)
```

### Test 3: DevEx account isolation
```bash
# Login to DevEx account as MH-Engineer
aws ec2 describe-instances --region us-east-1
# Expected: AccessDenied (if using Option 3)
# Expected: Success but empty (if using Option 1/2)

aws bedrock list-foundation-models --region us-east-1
# Expected: AccessDenied (all options)
```

---

## Questions

1. **Who should have Bedrock access?**
   - Separate permission set?
   - Separate AWS account entirely?
   - Request-based approval workflow?

2. **DevEx account purpose:**
   - Is it ONLY for Bedrock, or other experimentation too?
   - Should MH-Engineer/MH-Lead have ANY access to DevEx?

3. **Other AI services:**
   - Will you use SageMaker, Comprehend, Rekognition in future?
   - If yes, need separate permission set for those too?

4. **Audit requirement:**
   - Do you need to prove in audits that non-Bedrock accounts can't access AI?
   - If yes, Option 1 (explicit deny) is best evidence

---

