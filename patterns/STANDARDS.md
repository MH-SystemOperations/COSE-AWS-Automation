# COSE AWS Standards

**Enforced standards for all AWS resources created by COSE.**

## Tagging Standards

**ALL resources MUST have these 7 tags:**

| Tag | Purpose | Example |
|-----|---------|---------|
| `Owner` | Team responsible | `COSE` |
| `Department` | Business unit | `IT Operations` |
| `Application` | What it's for | `WorkSpaces Lifecycle Automation` |
| `Environment` | Environment | `prod`, `staging`, `qa`, `dev` |
| `CreatedBy` | How created | `CloudFormation`, `Terraform` |
| `ManagedBy` | What manages it | `COSE-AWS-Automation`, `IAC_project_xyz` |
| `CostCenter` | Billing | `Platform Engineering`, `Data Team` |

**Why these tags:**
- Cost allocation (CostCenter, Application)
- Ownership (Owner, Department)
- Automation (ManagedBy, CreatedBy)
- Environment isolation (Environment)

## Security Standards

### IAM Roles
- ✅ MUST have condition on `aws:SourceAccount` (prevent confused deputy)
- ✅ MUST have explicit trust policy (no wildcards)
- ✅ MUST have description
- ✅ MUST use managed policies where available
- ❌ NO inline policies (use AWS::IAM::Policy separately)

### DynamoDB
- ✅ MUST use encryption at rest (KMS)
- ✅ MUST have point-in-time recovery enabled
- ✅ MUST use PAY_PER_REQUEST (not provisioned)
- ❌ NO public access

### Lambda
- ✅ MUST have reserved concurrency (prevent runaway)
- ✅ MUST have timeout < 900 seconds
- ✅ MUST have description
- ✅ SHOULD use latest Python runtime (3.11+)

### SNS/SQS
- ✅ MUST use encryption (KMS)
- ✅ MUST have access policy (least privilege)

### S3
- ✅ MUST have encryption at rest
- ✅ MUST block public access
- ✅ MUST have versioning (prod only)
- ✅ MUST have lifecycle policies

## Cost Optimization Standards

### DynamoDB
- Use PAY_PER_REQUEST (not provisioned capacity)
- Add TTL for time-series data
- Enable auto-scaling if using provisioned

### Lambda
- Set reserved concurrency (prevent runaway costs)
- Right-size memory (test performance vs cost)
- Use ARM architecture where possible

### RDS
- Use t4g/t3 instances for non-prod
- Enable auto-scaling for prod
- Use Aurora Serverless v2 for variable workloads

## Naming Conventions

**CloudFormation Stacks:**
- Pattern: `{Application}-{Component}-{Environment}`
- Example: `WorkSpacesLifecycle-Orchestrator-Prod`

**Resources:**
- DynamoDB: PascalCase (`WorkSpacesLifecycleTracking`)
- Lambda: PascalCase (`WorkSpacesLifecycleManager`)
- IAM Roles: PascalCase (`WorkSpacesLifecycleManagerRole`)
- SNS/SQS: PascalCase (`WorkSpacesLifecycleNotifications`)

## Enforcement

**These standards are enforced through:**
1. Patterns in `/patterns` directory (pre-configured templates)
2. AWS Config rules (detect drift)
3. Code review (manual check)
4. (Future) Service Control Policies

**If you need an exception:**
- Document why in commit message
- Add comment in template explaining deviation
- Get approval from COSE team lead

## Examples

**Good:**
```yaml
Resources:
  MyTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: MyAppData
      BillingMode: PAY_PER_REQUEST
      SSESpecification:
        SSEEnabled: true
        SSEType: KMS
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      Tags:
        - Key: Owner
          Value: COSE
        # ... all 7 required tags
```

**Bad:**
```yaml
Resources:
  MyTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: MyAppData
      # Missing: encryption, PITR, tags
```

## Updates

Standards evolve through usage and failure (Principle #3: Blow Up the Rocket).

If a standard is blocking you, document the issue and propose an update.
