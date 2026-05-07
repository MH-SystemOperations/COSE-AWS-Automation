# Permission Set CloudFormation Templates

**These files define what each permission set can do.**  
Deployed automatically via GitHub Actions when pushed to `main`.

---

## Files

### 01-mh-security.yaml
**Role:** MH-Security  
**Purpose:** Security team access for audit and incident response  
**Session:** 8 hours

**Managed Policies:**
- `ViewOnlyAccess` - Read all AWS resources
- `SecurityAudit` - Additional security service read permissions

**Custom Permissions:**
- Full access to security services (GuardDuty, SecurityHub, Inspector, Macie, WAF, etc.)
- Security group & NACL management
- CloudTrail, Config, VPC Flow Logs management
- KMS key management
- IAM incident response (disable user access keys)

**Cannot:**
- Modify application infrastructure (Lambda, EC2, RDS, etc.)
- Deploy code
- Create/delete non-security resources

---

### 02-mh-engineer.yaml
**Role:** MH-Engineer  
**Purpose:** Base operational access for all engineers  
**Session:** 12 hours

**Managed Policies:**
- `ReadOnlyAccess` - Read all AWS resources

**Sandbox (123185598779):**
- Full access (`Action: "*"`)
- Blocked: Marketplace, VPC infrastructure changes, IAM users, secret reads

**Dev/QA (4 accounts):**
- Full write: Lambda, S3, DynamoDB, SQS, SNS, ECS, CloudFormation, Glue, Athena, etc.
- Create IAM roles (with `dev_boundary`)
- Read AND write secrets

**Production (5 accounts):**
- **Operational only** (no infrastructure deployment)
- Invoke Lambda (not create/modify)
- S3 objects (not buckets)
- DynamoDB items (not tables)
- SQS all operations
- Start/stop data jobs (Glue, Athena, DataBrew, Step Functions)
- Read logs
- List secrets (CANNOT read values)

**Guardrails (All Environments):**
- Cannot create IAM users
- Cannot remove permissions boundaries
- Cannot disable audit services
- Cannot create expensive instances
- Cannot create unencrypted EBS

---

### 03-mh-lead.yaml
**Role:** MH-Lead  
**Purpose:** Deployment access - everything MH-Engineer has + prod infrastructure deployment  
**Session:** 12 hours

**Managed Policies:**
- `ReadOnlyAccess` - Read all AWS resources

**Customer-Managed Policies:**
- `MH-Engineer-Guardrails` - Shared guardrails policy

**Sandbox & Dev/QA:**
- Same as MH-Engineer (full write)

**Production (5 accounts):**
- **Everything MH-Engineer has PLUS:**
- Deploy Lambda functions (create, update code, delete)
- Deploy CloudFormation stacks
- Deploy ECS services (push images, update task definitions)
- Deploy API Gateway
- Read AND update secrets (for key rotation)
- Create IAM roles with `dev_boundary` (data-prod and mh-ops only)
- Manage EventBridge/Scheduler rules
- Update SSM Parameter Store

**Additional Guardrails:**
- Cannot create EC2/RDS/S3 buckets directly (must use CloudFormation)
- Cannot create Lambda function URLs (security risk)
- Cannot create inline IAM policies in prod

---

### 04-mh-engineer-guardrails-stackset.yaml
**Type:** IAM Managed Policy (not a permission set)  
**Name:** MH-Engineer-Guardrails  
**Purpose:** Shared deny policy attached to MH-Lead

**What it blocks:**
- Access to Terraform state bucket
- Modifying permission set CloudFormation stacks
- SSO admin changes
- Identity Store changes
- IAM user creation
- Removing permissions boundaries
- Modifying boundary policies (`dev_boundary`, `data_engineer`)
- Updating AssumeRole policies
- Passing role to privileged roles
- AWS Organizations changes
- Account closure
- Audit service tampering (CloudTrail, GuardDuty, Config, SecurityHub)
- Data exfiltration (public snapshots, S3 replication, snapshot sharing)
- Network egress (VPC peering, VPN, Direct Connect, Transit Gateway)
- Expensive instances (GPU, HPC, inference, large memory)
- Expensive services (EMR, SageMaker tuning, Redshift)
- Unencrypted EBS volumes
- Cross-account AssumeRole (outside org o-vzuq8g0yfs)

**Deployed to:** Management account (mh-ops) only currently  
**TODO:** Deploy to all 13 accounts via script

---

## How Permissions Are Structured

### Layer 1: AWS Managed Policies
**Example:** `ReadOnlyAccess`  
**Purpose:** Baseline read access to all AWS services  
**Risk:** Auto-updates (AWS controls it)  
**Note:** Considering replacement with custom read-only policy

### Layer 2: Customer-Managed Policies
**Example:** `MH-Engineer-Guardrails`  
**Purpose:** Shared guardrails across multiple permission sets  
**File:** `../policies/mh-engineer-guardrails-v2.json`  
**Deployed:** Via CloudFormation stack `MH-Engineer-Guardrails`

### Layer 3: Inline Policies
**Location:** Inside each YAML file under `InlinePolicy`  
**Purpose:** Permission set-specific write permissions  
**Contains:** All the environment-based logic (sandbox/dev/qa/prod)

---

## Environment Detection

Permissions change based on AWS account ID:

```yaml
Condition:
  StringEquals:
    "aws:PrincipalAccount": "123185598779"  # Sandbox
```

**Sandbox:** 123185598779  
**Dev:** 201799325713 (data-dev), 686255955782 (pdt-dev)  
**QA:** 808468589041 (data-qa), 593793032905 (pdt-qa)  
**Prod:** 971318514578 (data-prod), 266565038828 (mh-ops), 209479269442 (pdt-staging), 476114142697 (pdt-prod), 339712701706 (pharmacy-prod)

See [../ACCOUNT-ENVIRONMENT-MAPPING.md](../ACCOUNT-ENVIRONMENT-MAPPING.md) for full list.

---

## Making Changes

### To Modify Permissions

1. Edit the appropriate YAML file
2. Commit to Git
3. Push to `main` branch
4. GitHub Actions deploys automatically (3-5 minutes)
5. IAM Identity Center provisions to accounts (5-10 minutes)

**Example: Add CodeBuild permissions to MH-Lead in Dev/QA:**

```yaml
# Edit 03-mh-lead.yaml, find DevQaFullWrite statement
{
  "Sid": "DevQaFullWrite",
  "Effect": "Allow",
  "Action": [
    "lambda:*",
    "codebuild:*",  # Add this line
    # ... rest of actions
  ],
  # ... rest of statement
}
```

### To Add New Environment

1. Identify account ID
2. Decide if it's sandbox/dev/qa/prod behavior
3. Add account ID to appropriate condition in YAML
4. Deploy

**Example: Add new dev account:**

```yaml
Condition:
  StringEquals:
    "aws:PrincipalAccount": [
      "201799325713",  # Existing data-dev
      "686255955782",  # Existing pdt-dev
      "999999999999"   # New dev account
    ]
```

---

## Testing Changes

### Sandbox Testing (Recommended)

1. Assign permission set to test user in sandbox only
2. Test changes in sandbox account (123185598779)
3. Verify permissions work as expected
4. Then assign to other accounts

### Dry-Run Deployment

```bash
# See what would change without applying
aws cloudformation deploy \
  --template-file 02-mh-engineer.yaml \
  --stack-name MH-Engineer-PermissionSet \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides DryRun=false \
  --no-execute-changeset \
  --profile mh-ops

# Review changeset
aws cloudformation describe-change-set \
  --change-set-name <name> \
  --stack-name MH-Engineer-PermissionSet \
  --profile mh-ops
```

---

## Troubleshooting

### "Inline policy too large (max 10KB)"
**Problem:** Hit CloudFormation inline policy size limit  
**Solution:** Move statements to customer-managed policy (like we did with guardrails)

### "Permission set not found"
**Problem:** Typo in permission set name  
**Solution:** Use exact names: `MH-Engineer`, `MH-Lead`, `MH-Security`

### "Cannot create customer managed policy reference"
**Problem:** Policy doesn't exist in target account  
**Solution:** Deploy `04-mh-engineer-guardrails-stackset.yaml` to account first

### "Changes not taking effect"
**Problem:** IAM Identity Center hasn't provisioned yet  
**Solution:** Wait 5-10 minutes, log out/in, or manually reprovision in console

---

## Security Notes

### Permissions Boundaries
All IAM role creation requires `dev_boundary` or `data_engineer` permissions boundary.  
This prevents privilege escalation - even if a role is created, it's constrained by the boundary.

### Guardrails Cannot Be Removed
Guardrails policy blocks:
- Removing permissions boundaries
- Modifying boundary policies themselves
- Modifying permission set CloudFormation stacks

### Region Lock
All actions restricted to `us-east-1` (data residency + cost control).

### Audit Trail
All actions logged in CloudTrail:
- Who did what
- When they did it
- Which permission set was used

---

