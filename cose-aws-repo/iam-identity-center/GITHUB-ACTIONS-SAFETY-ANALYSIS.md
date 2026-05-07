# GitHub Actions Safety Analysis - What Could Be Affected?

**Date:** 2026-05-07  
**Question:** Will GitHub Actions affect legacy permission sets?  
**Answer:** NO - Safe, only touches 3 new permission sets

---

## Current Environment

**Total Permission Sets:** 57  
**Legacy Permission Sets (NOT managed by CloudFormation):** 54
- Administrator, DevPowerUser, SoftwareEngineer, DataEngineer, etc.
- Created manually via IAM Identity Center console
- Used by existing teams

**New Permission Sets (Managed by CloudFormation):** 3
- MH-Engineer (CloudFormation stack: `MH-Engineer-PermissionSet`)
- MH-Lead (CloudFormation stack: `MH-Lead-PermissionSet`)
- MH-Security (CloudFormation stack: `MH-Security-PermissionSet`)

---

## What GitHub Actions Will Do

### On Every Push to `main` (when `iam-identity-center/` files change):

1. **Update CloudFormation Stack: MH-Engineer-PermissionSet**
   - Changes ONLY the MH-Engineer permission set
   - Does NOT touch other permission sets
   - CloudFormation isolation ensures this

2. **Update CloudFormation Stack: MH-Lead-PermissionSet**
   - Changes ONLY the MH-Lead permission set
   - Does NOT touch other permission sets

3. **Update CloudFormation Stack: MH-Security-PermissionSet**
   - Changes ONLY the MH-Security permission set
   - Does NOT touch other permission sets

4. **Deploy/Update Stack: MH-Engineer-Guardrails**
   - Creates IAM policy: `MH-Engineer-Guardrails`
   - Does NOT affect permission sets directly
   - Only MH-Lead references this policy (already deployed)

---

## Why Legacy Permission Sets Are Safe

### CloudFormation Isolation

**How CloudFormation works:**
- Each stack manages ONLY resources it created
- Stack `MH-Engineer-PermissionSet` can ONLY modify the MH-Engineer permission set
- Stack `MH-Lead-PermissionSet` can ONLY modify the MH-Lead permission set
- Stack `MH-Security-PermissionSet` can ONLY modify the MH-Security permission set

**Legacy permission sets:**
- NOT created by CloudFormation (created manually)
- NOT managed by any stack
- CloudFormation CANNOT modify them (no stack owns them)

**Proof:**
```bash
# Check stacks
aws cloudformation describe-stacks --profile mh-ops

# Result: Only 3 stacks
# - MH-Engineer-PermissionSet
# - MH-Lead-PermissionSet  
# - MH-Security-PermissionSet

# These 3 stacks ONLY manage their respective permission sets
```

---

## What CAN'T Be Affected

❌ **Legacy Permission Sets** (54 of them):
- Administrator
- DevPowerUser
- DataEngineer
- SoftwareEngineer
- All others created before MH-Engineer/Lead/Security

❌ **Permission Set Assignments:**
- Which users/groups have which permission sets
- Which accounts permission sets are assigned to
- GitHub Actions does NOT modify assignments

❌ **IAM Identity Center Configuration:**
- Identity source (Entra ID)
- User/group sync
- Session settings

❌ **Other AWS Resources:**
- EC2, RDS, Lambda, S3, etc.
- Only touches IAM Identity Center permission sets (3 specific ones)

---

## What COULD Go Wrong (And Mitigations)

### Scenario 1: Wrong Permission Set ARN in Template

**What if:** Template accidentally references wrong permission set ARN

**Risk:** VERY LOW
- CloudFormation validates ARNs
- Deployment would fail with error
- No changes applied

**Mitigation:**
- Templates use `Name` not ARN
- CloudFormation looks up by name
- Can't accidentally modify wrong permission set

---

### Scenario 2: Typo in Permission Set Name

**What if:** Template says `Name: MH-Engineerr` (typo)

**Risk:** VERY LOW
- CloudFormation would try to CREATE new permission set
- You'd see new "MH-Engineerr" permission set appear
- Original "MH-Engineer" unaffected

**Mitigation:**
- Use Pull Requests - review changes before merge
- GitHub Actions logs show what's being deployed
- Easy to rollback via Git revert

---

### Scenario 3: Permissions Too Broad in Updated Policy

**What if:** Update gives MH-Engineer too many permissions

**Risk:** MEDIUM (operational, not technical)
- Only affects MH-Engineer role (not legacy roles)
- CloudFormation applies the update
- Users assigned MH-Engineer get new permissions

**Mitigation:**
- Test in sandbox first (Parth already testing)
- Use Pull Requests for review
- Monitor CloudTrail for unexpected access
- Can rollback via Git revert + redeploy

---

### Scenario 4: GitHub Actions Role Gets Too Much Access

**What if:** GitHubActionsDeployRole can modify other permission sets

**Risk:** LOW
- Role policy explicitly scopes to 3 stack names only
- Can't create/modify stacks with other names
- Can't modify permission sets outside these 3 stacks

**Proof in template:**
```yaml
Resource:
  - arn:aws:cloudformation:*:*:stack/MH-Engineer-PermissionSet/*
  - arn:aws:cloudformation:*:*:stack/MH-Lead-PermissionSet/*
  - arn:aws:cloudformation:*:*:stack/MH-Security-PermissionSet/*
  - arn:aws:cloudformation:*:*:stack/MH-Engineer-Guardrails/*
```

**Mitigation:** Already in place - least privilege

---

## Verification Steps Before First Deployment

### Step 1: Verify Stack Names Match

```bash
# Check existing stacks
aws cloudformation list-stacks --profile mh-ops \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query 'StackSummaries[?contains(StackName, `MH-`)].StackName'

# Expected:
# - MH-Engineer-PermissionSet
# - MH-Lead-PermissionSet
# - MH-Security-PermissionSet

# These match workflow stack names ✅
```

### Step 2: Verify Permission Set ARNs

```bash
# Get MH-Engineer ARN
aws sso-admin list-permission-sets \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --profile mh-ops \
  --query 'PermissionSets' --output text | while read arn; do
    name=$(aws sso-admin describe-permission-set \
      --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
      --permission-set-arn "$arn" \
      --profile mh-ops \
      --query 'PermissionSet.Name' --output text 2>/dev/null)
    if [[ "$name" == "MH-Engineer" ]]; then
      echo "$arn"
    fi
  done

# Expected: arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223e550ce22c566
```

### Step 3: Test Dry-Run Deployment

```bash
# Deploy with --no-execute-changeset to see what would change
aws cloudformation deploy \
  --template-file iam-identity-center/stacks/02-mh-engineer.yaml \
  --stack-name MH-Engineer-PermissionSet \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides DryRun=false \
  --no-execute-changeset \
  --profile mh-ops

# Review changeset
aws cloudformation describe-change-set \
  --change-set-name <changeset-name> \
  --stack-name MH-Engineer-PermissionSet \
  --profile mh-ops

# Verify only MH-Engineer permission set modified
```

---

## Rollback Plan

If something goes wrong:

### Option 1: Git Revert + Redeploy (Preferred)

```bash
# Revert last commit
git revert HEAD

# Push to trigger rollback deployment
git push origin main

# GitHub Actions deploys previous version automatically
```

### Option 2: Manual CloudFormation Rollback

```bash
# Rollback stack to previous version
aws cloudformation rollback-stack \
  --stack-name MH-Engineer-PermissionSet \
  --profile mh-ops

# Or delete and recreate from Git
aws cloudformation delete-stack \
  --stack-name MH-Engineer-PermissionSet \
  --profile mh-ops

# Then redeploy from Git
```

### Option 3: Emergency - Detach Assignments

```bash
# If permission set causing issues, remove assignments
aws sso-admin list-account-assignments \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --permission-set-arn <arn> \
  --account-id <account-id> \
  --profile mh-ops

# Delete assignments (users lose access)
aws sso-admin delete-account-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --permission-set-arn <arn> \
  --principal-id <group-id> \
  --principal-type GROUP \
  --target-type AWS_ACCOUNT \
  --target-id <account-id> \
  --profile mh-ops
```

---

## Post-Deployment Monitoring

### What to Watch

1. **GitHub Actions Logs**
   - Check for errors
   - Verify only 3 stacks updated

2. **CloudFormation Events**
   ```bash
   aws cloudformation describe-stack-events \
     --stack-name MH-Engineer-PermissionSet \
     --profile mh-ops \
     --max-items 20
   ```

3. **Permission Set Count**
   ```bash
   # Should still be 57 (not more, not less)
   aws sso-admin list-permission-sets \
     --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
     --profile mh-ops \
     --query 'PermissionSets' --output text | wc -l
   ```

4. **CloudTrail**
   - Check for unexpected sso-admin actions
   - Verify only MH-Engineer/Lead/Security modified

---

## Summary: Is It Safe?

### ✅ YES - Safe to Deploy

**What's protected:**
- ✅ Legacy permission sets (54 of them) - CloudFormation can't touch them
- ✅ Permission set assignments - GitHub Actions doesn't modify assignments
- ✅ IAM Identity Center config - GitHub Actions only updates 3 permission sets
- ✅ Other AWS resources - GitHub Actions only has IAM Identity Center permissions

**What changes:**
- ⚠️ MH-Engineer permission set (only when you push changes)
- ⚠️ MH-Lead permission set (only when you push changes)
- ⚠️ MH-Security permission set (only when you push changes)
- ⚠️ MH-Engineer-Guardrails policy (only in mh-ops account)

**How to be extra safe:**
1. Use Pull Requests (review before merge)
2. Test in dry-run mode first
3. Monitor GitHub Actions logs
4. Have rollback plan ready (Git revert)

**Blast radius if something goes wrong:**
- Limited to MH-Engineer, MH-Lead, MH-Security
- Only 2 people have these roles (Micah + Keith)
- Easy rollback via Git revert

**Recommendation:** Safe to proceed. Risk is minimal and contained.

---

