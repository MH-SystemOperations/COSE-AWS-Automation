# GitHub Actions Deployment - Simple Setup Guide

**Goal:** Push to `main` branch → Permission sets automatically deploy  
**Time:** 10 minutes one-time setup

---

## What This Does

When you push changes to `iam-identity-center/stacks/` or `iam-identity-center/policies/`:
1. GitHub Actions automatically runs
2. Deploys MH-Engineer, MH-Lead, MH-Security permission sets
3. Deploys guardrails policy
4. IAM Identity Center automatically provisions to accounts

**No manual CloudFormation deployment needed.**

---

## One-Time Setup (Do Once)

### Step 1: Deploy GitHub Actions Role (5 minutes)

This allows GitHub to deploy permission sets on your behalf.

```bash
cd cose-aws-repo

# Deploy the OIDC role
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

**What this does:**
- Creates `GitHubActionsDeployRole` in mh-ops account (266565038828)
- Allows GitHub Actions from your repo to assume this role
- Gives permission to deploy CloudFormation stacks for permission sets

### Step 2: Push to GitHub (2 minutes)

```bash
git add .github/
git commit -m "feat: Add GitHub Actions for permission set deployment"
git push origin main
```

### Step 3: Verify (2 minutes)

1. Go to GitHub: `https://github.com/MH-SystemOperations/COSE-AWS-Automation/actions`
2. You should see "Deploy IAM Permission Sets" workflow
3. It will run automatically on the push
4. Check logs to verify deployment succeeded

---

## How to Use (Daily Workflow)

### Making Changes

1. **Edit permission set YAML**
   ```bash
   cd cose-aws-repo
   vim iam-identity-center/stacks/03-mh-lead.yaml
   # Make your changes
   ```

2. **Commit and push**
   ```bash
   git add iam-identity-center/
   git commit -m "feat: Add CodeBuild permissions to MH-Lead"
   git push origin main
   ```

3. **GitHub Actions deploys automatically**
   - Go to GitHub Actions tab
   - Watch deployment progress
   - Takes ~3-5 minutes

4. **Done** - Permission sets updated in all accounts

---

## What Gets Deployed

When you push to `main`:

✅ **Always deploys:**
- `02-mh-engineer.yaml` → MH-Engineer permission set
- `03-mh-lead.yaml` → MH-Lead permission set  
- `01-mh-security.yaml` → MH-Security permission set
- `04-mh-engineer-guardrails-stackset.yaml` → Guardrails policy

✅ **Only if files changed:**
- GitHub Actions detects which files changed
- Only runs deployment if `iam-identity-center/stacks/**` or `iam-identity-center/policies/**` modified

---

## Manual Deployment (Fallback)

If GitHub Actions fails or you want to deploy manually:

```bash
# Deploy permission sets
aws cloudformation deploy \
  --template-file iam-identity-center/stacks/02-mh-engineer.yaml \
  --stack-name MH-Engineer-PermissionSet \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides DryRun=false \
  --region us-east-1 \
  --profile mh-ops

aws cloudformation deploy \
  --template-file iam-identity-center/stacks/03-mh-lead.yaml \
  --stack-name MH-Lead-PermissionSet \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides DryRun=false \
  --region us-east-1 \
  --profile mh-ops

# Deploy guardrails (mh-ops only - not multi-account yet)
aws cloudformation deploy \
  --template-file iam-identity-center/stacks/04-mh-engineer-guardrails-stackset.yaml \
  --stack-name MH-Engineer-Guardrails \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1 \
  --profile mh-ops
```

---

## Guardrails Multi-Account Deployment (TODO)

**Current state:** Guardrails policy only deploys to mh-ops (266565038828)

**Why:** GitHub Actions role only has access to management account

**To deploy to all 13 accounts:**

### Option A: Manual script (use now)
```bash
./scripts/deploy-guardrails-simple.sh
```

### Option B: GitHub Actions cross-account (future enhancement)
- Set up OrganizationAccountAccessRole trust
- Update workflow to assume role per account
- Deploy guardrails to all 13 accounts automatically

**Recommendation:** Use Option A (manual script) for now. Only 1 policy, doesn't change often.

---

## Troubleshooting

### "Role cannot be assumed by GitHub Actions"

**Problem:** OIDC provider not set up or repo name mismatch

**Fix:**
1. Verify OIDC provider exists:
   ```bash
   aws iam list-open-id-connect-providers --profile mh-ops
   ```
2. Check role trust policy allows your repo:
   ```bash
   aws iam get-role --role-name GitHubActionsDeployRole --profile mh-ops
   ```
3. Verify repo name matches: `MH-SystemOperations/COSE-AWS-Automation`

---

### "CloudFormation stack already exists"

**Problem:** Stack created manually, GitHub Actions trying to create

**Fix:**
```bash
# Update existing stack instead of creating
aws cloudformation update-stack \
  --stack-name MH-Engineer-PermissionSet \
  --template-body file://iam-identity-center/stacks/02-mh-engineer.yaml \
  --capabilities CAPABILITY_IAM \
  --profile mh-ops
```

Or delete and let GitHub Actions recreate:
```bash
aws cloudformation delete-stack --stack-name MH-Engineer-PermissionSet --profile mh-ops
# Then push to GitHub
```

---

### "Permission denied to modify permission set"

**Problem:** GitHub Actions role lacks permissions

**Fix:** Redeploy the OIDC role with updated permissions:
```bash
aws cloudformation deploy \
  --template-file .github/workflows/setup-github-oidc-role.yaml \
  --stack-name GitHubActionsDeployRole \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile mh-ops
```

---

## Security Notes

**What GitHub Actions CAN do:**
- ✅ Deploy/update MH-Engineer, MH-Lead, MH-Security permission sets
- ✅ Deploy/update MH-Engineer-Guardrails policy (mh-ops only)
- ✅ Read IAM Identity Center configuration

**What GitHub Actions CANNOT do:**
- ❌ Assign permission sets to users/groups
- ❌ Create new permission sets (only update these 3)
- ❌ Modify other IAM policies
- ❌ Access to other accounts (only mh-ops)

**Audit trail:**
- All deployments logged in CloudTrail
- GitHub Actions logs show who pushed what
- CloudFormation change sets show exactly what changed

---

## Best Practices

### 1. Use Pull Requests
```bash
# Create branch for changes
git checkout -b feature/add-codebuild-permissions

# Make changes
vim iam-identity-center/stacks/03-mh-lead.yaml

# Commit and push
git add .
git commit -m "feat: Add CodeBuild permissions to MH-Lead"
git push origin feature/add-codebuild-permissions

# Open PR on GitHub
# Get review
# Merge → Auto-deploys
```

### 2. Test in Sandbox First
- Create test permission set in sandbox
- Verify changes work
- Apply to prod permission sets

### 3. Monitor Deployments
- Watch GitHub Actions logs
- Check AWS console for stack events
- Verify permission set provisioning completes

### 4. Document Changes
- Use descriptive commit messages
- Add comments to YAML files explaining why
- Update SIMPLE-PERMISSIONS-GUIDE.md if access changes

---

## What's NOT Automated (Yet)

These still require manual steps:

1. **User/Group assignments** - Assign permission sets to users via console or CLI
2. **Guardrails multi-account** - Deploy to all 13 accounts via script
3. **Permission set provisioning** - IAM Identity Center auto-provisions but can take 5-10 minutes

---

## Summary

**Setup:** Deploy GitHub OIDC role once (10 minutes)  
**Daily use:** Edit YAML, git push, done (3 minutes)  
**Result:** Permission sets stay in sync with Git (source of truth)

**No more:**
- ❌ Manual CloudFormation console deployments
- ❌ Configuration drift (like Awad adding 3 policies this morning)
- ❌ "Did we deploy the latest version?" questions

**Git is source of truth. Push to main = deployed to AWS.**

---

