# Pre-Deployment Checklist - GitHub Actions Setup

**Before pushing to GitHub, verify these steps are complete.**

---

## ✅ Pre-Deployment Steps

### 1. Files Organized
- [ ] Old docs moved to `archive/`
- [ ] Only essential files in main directory
- [ ] READMEs created (`README.md`, `stacks/README.md`)
- [ ] GitHub Actions workflow in `.github/workflows/`

### 2. GitHub OIDC Role Deployed

```bash
# Deploy the role that allows GitHub to deploy on our behalf
cd cose-aws-repo

aws cloudformation deploy \
  --template-file .github/workflows/setup-github-oidc-role.yaml \
  --stack-name GitHubActionsDeployRole \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1 \
  --profile mh-ops \
  --parameter-overrides \
    GitHubOrg=MH-SystemOperations \
    GitHubRepo=COSE-AWS-Automation
```

**Verify:**
```bash
aws iam get-role --role-name GitHubActionsDeployRole --profile mh-ops
```

Expected output: Role exists with OIDC trust policy

---

### 3. CloudFormation Stacks Exist

```bash
# Verify existing stacks
aws cloudformation describe-stacks --profile mh-ops --region us-east-1 \
  --query 'Stacks[?contains(StackName, `MH-`)].{Name:StackName,Status:StackStatus}' \
  --output table
```

**Expected output:**
```
--------------------------------------------------
|                 DescribeStacks                 |
+----------------------------+-------------------+
|            Name            |      Status       |
+----------------------------+-------------------+
|  MH-Lead-PermissionSet     |  UPDATE_COMPLETE  |
|  MH-Engineer-PermissionSet |  UPDATE_COMPLETE  |
|  MH-Security-PermissionSet |  CREATE_COMPLETE  |
+----------------------------+-------------------+
```

✅ All 3 permission set stacks exist

---

### 4. Verify No Unintended Changes in YAML

```bash
# Check what's actually in the templates
cd iam-identity-center/stacks

# Verify MH-Engineer has only ReadOnlyAccess
grep -A 2 "ManagedPolicies:" 02-mh-engineer.yaml

# Expected:
#   ManagedPolicies:
#     - arn:aws:iam::aws:policy/ReadOnlyAccess

# Verify MH-Lead has only ReadOnlyAccess (no bad policies)
grep -A 5 "ManagedPolicies:" 03-mh-lead.yaml

# Expected:
#   ManagedPolicies:
#     - arn:aws:iam::aws:policy/ReadOnlyAccess
# (Should NOT see AmazonS3FullAccess, AdministratorAccess-AWSElasticBeanstalk, etc.)
```

✅ Only intended managed policies present

---

### 5. Test Deployment Locally (Optional but Recommended)

```bash
# Dry-run to see what would change
aws cloudformation deploy \
  --template-file iam-identity-center/stacks/02-mh-engineer.yaml \
  --stack-name MH-Engineer-PermissionSet \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides DryRun=false \
  --no-execute-changeset \
  --region us-east-1 \
  --profile mh-ops

# Should show: No changes (if templates match deployed state)
# Or: Show specific changes being made
```

✅ Dry-run successful, changes expected

---

## 🚀 Deployment Steps

### Step 1: Commit and Push

```bash
cd cose-aws-repo

# Stage files
git add .github/
git add iam-identity-center/
git add scripts/

# Check what's being committed
git status

# Verify only intended files
git diff --cached --name-only

# Commit
git commit -m "feat: Add GitHub Actions for permission set deployment

- Automated deployment via GitHub Actions
- OIDC role for secure GitHub access
- Organized documentation structure
- Clean directory (archived old docs)
- Safe deployment (only touches 3 permission sets)
"

# Push to GitHub
git push origin main
```

---

### Step 2: Monitor GitHub Actions

1. Go to: https://github.com/MH-SystemOperations/COSE-AWS-Automation/actions
2. Find "Deploy IAM Permission Sets" workflow
3. Click on the running job
4. Watch logs in real-time

**Expected duration:** 3-5 minutes

---

### Step 3: Verify Deployment

```bash
# Check CloudFormation stacks updated
aws cloudformation describe-stacks --profile mh-ops --region us-east-1 \
  --query 'Stacks[?contains(StackName, `MH-`)].{Name:StackName,Status:StackStatus,Updated:LastUpdatedTime}' \
  --output table

# Should show recent LastUpdatedTime
```

---

### Step 4: Verify Permission Sets

```bash
# List managed policies on MH-Lead (verify bad ones removed)
aws sso-admin list-managed-policies-in-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-7223d1577aba4b38/ps-7223f99c07c1a588 \
  --profile mh-ops

# Expected:
# - ReadOnlyAccess

# Should NOT see:
# - AmazonS3FullAccess
# - AdministratorAccess-AWSElasticBeanstalk
# - AWSCodeBuildAdminAccess
```

---

### Step 5: Test in AWS Console

1. Log into AWS console with MH-Lead role
2. Try to access S3 in sandbox → Should work
3. Try to deploy Elastic Beanstalk in sandbox → Should work
4. Try to create IAM user → Should be denied (guardrails)

✅ Permissions work as expected

---

## 🔥 Rollback Plan (If Needed)

### If GitHub Actions Fails

```bash
# Option 1: Fix and push again
git commit --amend
git push origin main --force

# Option 2: Revert commit
git revert HEAD
git push origin main

# Option 3: Manual rollback
aws cloudformation rollback-stack \
  --stack-name MH-Engineer-PermissionSet \
  --profile mh-ops
```

---

### If Permissions Break

```bash
# Remove permission set assignments temporarily
aws sso-admin delete-account-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-7223d1577aba4b38 \
  --permission-set-arn <arn> \
  --principal-id <group-id> \
  --principal-type GROUP \
  --target-type AWS_ACCOUNT \
  --target-id <account-id> \
  --profile mh-ops

# Users lose access until fixed and reassigned
```

---

## ✅ Success Criteria

After deployment:

- [ ] GitHub Actions workflow completed successfully
- [ ] All 3 CloudFormation stacks show UPDATE_COMPLETE or CREATE_COMPLETE
- [ ] MH-Lead has only ReadOnlyAccess + MH-Engineer-Guardrails (no bad policies)
- [ ] Permission sets work in AWS console (can access assigned accounts)
- [ ] Guardrails work (cannot create IAM user)
- [ ] No errors in CloudTrail
- [ ] 57 total permission sets still exist (not 58, not 56 - no accidental creates/deletes)

---

## 📊 Post-Deployment Monitoring

### First 24 Hours

- Monitor GitHub Actions for any unexpected runs
- Check CloudTrail for permission set modifications
- Monitor Slack/Teams for user access issues
- Review IAM Identity Center audit logs

### First Week

- Verify no configuration drift
- Ensure no manual console changes
- Confirm Git is source of truth
- Document any issues encountered

---

## 📞 Emergency Contacts

**If deployment goes wrong:**
- Micah Burkhardt (you)
- Keith Ferguson (test user)
- AWS Support (if infrastructure issue)

**Recovery time objective:** < 30 minutes (via Git revert)

---

