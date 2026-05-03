# COSE CloudFormation Patterns

**Reusable, secure, standardized CloudFormation templates.**

## Purpose

These patterns are the "paved path" for AWS resource creation. They enforce COSE governance standards:
- Security hardening by default
- Consistent tagging
- Encryption at rest
- Least privilege IAM
- Cost-optimized settings

**Use these patterns** instead of creating resources from scratch.

## Available Patterns

### DynamoDB
- **`dynamodb/secure-table.yaml`** - Standard DynamoDB table
  - Encryption at rest (KMS)
  - Point-in-time recovery
  - PAY_PER_REQUEST billing
  - Standard tags

### IAM
- **`iam/lambda-execution-role.yaml`** - Lambda execution role
  - Condition on SourceAccount
  - Basic execution policy only
  - Standard tags
  - Add custom policies separately

### Lambda
- (Coming soon) Standard Lambda function template

## Usage

**Copy and customize parameters:**

```bash
# Create DynamoDB table
aws cloudformation create-stack \
  --stack-name my-app-tracking-table \
  --template-body file://patterns/dynamodb/secure-table.yaml \
  --parameters \
    ParameterKey=TableName,ParameterValue=MyAppTracking \
    ParameterKey=ApplicationTag,ParameterValue="My Application" \
  --profile mh-ops \
  --region us-east-1
```

**Or use as nested stack:**

```yaml
Resources:
  TrackingTable:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/.../secure-table.yaml
      Parameters:
        TableName: MyAppTracking
        ApplicationTag: My Application
```

## Standards Enforced

All patterns enforce:
- **Encryption**: KMS encryption at rest (minimum)
- **Tags**: Owner, Department, Application, Environment, CreatedBy, ManagedBy
- **Billing**: Cost-optimized defaults (PAY_PER_REQUEST for DynamoDB)
- **Security**: Least privilege, conditions on trust policies
- **Audit**: Point-in-time recovery, CloudTrail integration

## Customization

**Parameters are the customization points:**
- TableName, RoleName - resource names
- ApplicationTag - what this is for
- EnvironmentTag - dev/qa/staging/prod
- OwnerTag - team name (defaults to COSE)

**Standards are NOT parameters** (encryption, tags, PITR) - these are enforced.

## Adding New Patterns

When creating a new pattern:
1. Start from an existing pattern (copy structure)
2. Add security defaults (encryption, least privilege)
3. Add standard tags (all 7 required)
4. Document in comments what's enforced vs customizable
5. Test in dev account first

## Contributing

If you need a resource type not listed here, create a pattern and PR it.

**Good pattern characteristics:**
- One resource type per template (composable)
- Security hardened by default
- Parameters for customization, not security settings
- Comments explaining enforced standards
- Exports for cross-stack references
