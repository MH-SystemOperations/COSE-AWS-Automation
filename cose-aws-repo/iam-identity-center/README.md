# IAM Identity Center Permission Sets

**Automated deployment via GitHub Actions** - Push to `main` branch deploys changes automatically.

---

## Quick Links

- **[Simple Permissions Guide](SIMPLE-PERMISSIONS-GUIDE.md)** - What each role can/can't do
- **[GitHub Deployment Guide](GITHUB-DEPLOYMENT-GUIDE.md)** - How to deploy changes
- **[Production Access Review](PROD-ACCESS-REVIEW.md)** - Security analysis

---

## Our 3 Permission Sets

### MH-Engineer (Operational Access)
- **Who:** All engineers
- **Purpose:** Daily operations - troubleshoot, run jobs, fix data
- **Prod:** Read + limited operational writes (invoke Lambda, S3 objects, DynamoDB items)
- **Dev/QA:** Full write access
- **[Details →](stacks/README.md#mh-engineer)**

### MH-Lead (Deployment Access)
- **Who:** Senior engineers, deployers
- **Purpose:** Everything MH-Engineer can do + deploy code to production
- **Prod:** Deploy Lambda/CloudFormation/ECS, read secrets, create IAM roles
- **Dev/QA:** Full write access (same as Engineer)
- **[Details →](stacks/README.md#mh-lead)**

### MH-Security (Security Team)
- **Who:** Security team
- **Purpose:** Security audit, incident response
- **All Accounts:** Full security services, can't modify application infrastructure
- **[Details →](stacks/README.md#mh-security)**

---

## How to Make Changes

### Option 1: GitHub (Recommended)

1. Edit files in `iam-identity-center/stacks/`
2. Commit and push to `main` branch
3. GitHub Actions automatically deploys
4. Takes 3-5 minutes

**[Full guide →](GITHUB-DEPLOYMENT-GUIDE.md)**

### Option 2: Manual Deployment

```bash
cd cose-aws-repo

# Deploy permission sets
aws cloudformation deploy \
  --template-file iam-identity-center/stacks/02-mh-engineer.yaml \
  --stack-name MH-Engineer-PermissionSet \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides DryRun=false \
  --region us-east-1 \
  --profile mh-ops
```

---

## Directory Structure

```
iam-identity-center/
├── README.md                           ← You are here
├── SIMPLE-PERMISSIONS-GUIDE.md         ← What each role can do
├── GITHUB-DEPLOYMENT-GUIDE.md          ← How to deploy
├── PROD-ACCESS-REVIEW.md               ← Security analysis
├── GITHUB-ACTIONS-SAFETY-ANALYSIS.md   ← Safety verification
├── AI-ACCESS-POLICY.md                 ← AI services (Bedrock) policy
├── ACCOUNT-ENVIRONMENT-MAPPING.md      ← Which accounts are dev/qa/prod
│
├── stacks/                             ← CloudFormation templates (what gets deployed)
│   ├── README.md                       ← Details on each permission set
│   ├── 01-mh-security.yaml            ← Security team role
│   ├── 02-mh-engineer.yaml            ← Base engineering role
│   ├── 03-mh-lead.yaml                ← Elevated deployment role
│   └── 04-mh-engineer-guardrails-stackset.yaml  ← Guardrails policy
│
├── policies/                           ← Policy files
│   └── mh-engineer-guardrails-v2.json ← Current guardrails (referenced by stacks)
│
└── archive/                            ← Old docs (ignore)
```

---

## Key Concepts

### Guardrails (Security Boundaries)
**What:** Deny policies that block dangerous actions org-wide  
**Examples:** Can't create IAM users, can't disable CloudTrail, can't use expensive instances  
**Applied to:** All 3 permission sets  
**File:** `policies/mh-engineer-guardrails-v2.json`

### Environment-Based Permissions
**Sandbox:** Almost everything (experiment freely)  
**Dev/QA:** Full write (build and test)  
**Prod:** Read + operational (Engineer) or deployment (Lead)

### CloudFormation-First in Prod
**Rule:** Can't create EC2/RDS/S3 buckets directly in prod  
**Why:** Forces infrastructure as code  
**How:** Use CloudFormation stacks for infrastructure

---

## Who Has What

**Current assignments (TEST phase):**
- Micah Burkhardt: MH-Engineer + MH-Lead
- Keith Ferguson: MH-Engineer + MH-Lead

**Rollout plan:**
1. Test phase: Micah + Keith only (current)
2. Platform Data team: 3-4 weeks
3. Platform Digital Tools team: After Platform Data success
4. Other teams: TBD

---

## Security

### What's Protected
✅ Legacy permission sets untouched (54 others in IAM Identity Center)  
✅ Root user protections (guardrails apply even to root)  
✅ Audit logging protected (can't disable CloudTrail/GuardDuty)  
✅ Permissions boundaries required (can't escalate privileges)  
✅ Region locked to us-east-1 (cost control + data residency)

### What's Monitored
- CloudTrail logs all actions
- GitHub Actions logs all deployments
- Only authorized repos can deploy (OIDC)

---

## Troubleshooting

### "Access Denied"
1. Check which role you're using (Engineer vs Lead)
2. Check which account (sandbox/dev/qa vs prod)
3. Review [Simple Permissions Guide](SIMPLE-PERMISSIONS-GUIDE.md)

### "GitHub Actions Failed"
1. Check Actions tab: https://github.com/MH-SystemOperations/COSE-AWS-Automation/actions
2. Review error logs
3. See [GitHub Deployment Guide](GITHUB-DEPLOYMENT-GUIDE.md#troubleshooting)

### "Permission Set Not Provisioned"
IAM Identity Center takes 5-10 minutes to provision after CloudFormation deploys.  
Wait a few minutes, then log out/in to AWS console.

---

## Questions?

**For access issues:** Check [Simple Permissions Guide](SIMPLE-PERMISSIONS-GUIDE.md)  
**For deployment:** Check [GitHub Deployment Guide](GITHUB-DEPLOYMENT-GUIDE.md)  
**For security review:** Check [Prod Access Review](PROD-ACCESS-REVIEW.md)

---

