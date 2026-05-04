# StackSet Infrastructure Roles

**Purpose:** Enable CloudFormation StackSets to deploy resources across multiple AWS accounts from a central management account.

## What are StackSets?

StackSets allow you to deploy the same CloudFormation template to multiple AWS accounts/regions with a single operation. Instead of manually deploying a stack in each account, you define it once and StackSets handle the deployment.

**Use cases:**
- Cross-account IAM roles (e.g., WorkSpaces lifecycle automation)
- Security baselines (GuardDuty, Config rules, CloudTrail)
- Compliance controls (SCPs, tag policies)
- Shared infrastructure (VPC peering, cross-account access)

## Architecture

```
Management Account (mh-ops)
├── AWSCloudFormationStackSetAdministrationRole
│   └── Assumes → Target Account ExecutionRole
│
Target Accounts (data-prod, pharmacy-prod, etc.)
└── AWSCloudFormationStackSetExecutionRole
    └── Creates/updates/deletes resources
```

## Security Model

**Administration Role (management account):**
- Only CloudFormation service can assume it
- Only permission: assume the execution role in target accounts
- Cannot directly create resources

**Execution Role (target accounts):**
- Only management account's administration role can assume it
- Has AdministratorAccess (AWS recommended approach)
- Creates resources on behalf of StackSets

**Why AdministratorAccess?**
- StackSets need flexibility to create any resource type
- CloudFormation validates templates before deployment
- Actual permissions depend on what templates you deploy
- This is AWS's standard pattern (not a COSE deviation)

## One-Time Setup (Do This Once)

### Step 1: Deploy Administration Role (Management Account)

```bash
cd C:\Users\micah.burkhardt\OneDrive\ -\ Marathon\ Health\Desktop\COSE-AWS-Automation
aws cloudformation create-stack \
  --stack-name StackSetAdministrationRole \
  --template-body file://patterns/stacksets/administration-role.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile mh-ops --region us-east-1
```

Wait for completion:
```bash
aws cloudformation wait stack-create-complete \
  --stack-name StackSetAdministrationRole \
  --profile mh-ops --region us-east-1
```

### Step 2: Deploy Execution Role (Each Target Account)

**Account: mh-ops (266565038828)**
```bash
aws cloudformation create-stack \
  --stack-name StackSetExecutionRole \
  --template-body file://patterns/stacksets/execution-role.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile mh-ops --region us-east-1
```

**Account: data-prod (971318514578)**
```bash
aws cloudformation create-stack \
  --stack-name StackSetExecutionRole \
  --template-body file://patterns/stacksets/execution-role.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile data-prod --region us-east-1
```

**Account: pharmacy-prod (480202104756)**
```bash
aws cloudformation create-stack \
  --stack-name StackSetExecutionRole \
  --template-body file://patterns/stacksets/execution-role.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile pharmacy-prod --region us-east-1
```

Wait for all to complete:
```bash
aws cloudformation wait stack-create-complete --stack-name StackSetExecutionRole --profile mh-ops --region us-east-1
aws cloudformation wait stack-create-complete --stack-name StackSetExecutionRole --profile data-prod --region us-east-1
aws cloudformation wait stack-create-complete --stack-name StackSetExecutionRole --profile pharmacy-prod --region us-east-1
```

### Step 3: Verify Setup

```bash
# Check administration role exists in management account
aws iam get-role --role-name AWSCloudFormationStackSetAdministrationRole --profile mh-ops

# Check execution roles exist in target accounts
aws iam get-role --role-name AWSCloudFormationStackSetExecutionRole --profile mh-ops
aws iam get-role --role-name AWSCloudFormationStackSetExecutionRole --profile data-prod
aws iam get-role --role-name AWSCloudFormationStackSetExecutionRole --profile pharmacy-prod
```

## Using StackSets (After Setup)

Once the roles are deployed, you can create StackSets:

```bash
# Create StackSet
aws cloudformation create-stack-set \
  --stack-set-name MyStackSet \
  --template-body file://my-template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile mh-ops --region us-east-1

# Deploy to accounts
aws cloudformation create-stack-instances \
  --stack-set-name MyStackSet \
  --accounts 266565038828 971318514578 480202104756 \
  --regions us-east-1 \
  --profile mh-ops
```

## Safety Considerations

**✅ Safe:**
- Only CloudFormation service can use these roles (not users, not Lambdas)
- Must go through StackSet API (audit trail in CloudTrail)
- Templates validated before deployment
- Can set failure tolerance (stop if X accounts fail)

**⚠️ Risks:**
- Execution role has broad permissions (by design)
- Bad template can affect multiple accounts
- Failed deployments may leave partial state

**Mitigation:**
- Always test templates in one account first
- Use `--failure-tolerance-count` parameter
- Review StackSet operations in CloudFormation console
- Templates in version control (this repo)

## Troubleshooting

**"Account should have 'AWSCloudFormationStackSetAdministrationRole'"**
→ Deploy administration-role.yaml in management account

**"AccessDenied when assuming execution role"**
→ Deploy execution-role.yaml in target account

**"Role already exists" error**
→ Roles may have been created manually. Delete and recreate with these templates for consistency.

## References

- [AWS StackSets Documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html)
- [StackSet Prerequisites](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-prereqs.html)
- COSE Gov Principle #1: Guardrails over approvals (automate where safe)
