# Tag-Based Environment Access Control

## Why Tags > Accounts

**Old thinking**: Control access by AWS account
- Production account = restricted
- Dev account = full access

**Problem**: Resources in "wrong" account break the model
- Test database in prod account (for performance testing)
- Production data replicated to dev account (for analysis)

**New thinking**: Control access by resource tags
- `mh:environment: prod` = restricted
- `mh:environment: dev` = full access
- **Works across all accounts**

---

## How It Works

### Developer Permission (Example)

**Can do**:
```bash
# Read S3 bucket tagged mh:environment=dev
aws s3 cp s3://my-bucket/file.txt . ✅

# Write to RDS tagged mh:environment=qa
aws rds modify-db-instance --db-instance-id mydb ✅

# Connect to EC2 tagged mh:environment=sandbox
aws ssm start-session --target i-abc123 ✅
```

**Cannot do**:
```bash
# Read S3 bucket tagged mh:environment=prod
aws s3 cp s3://prod-bucket/file.txt . ❌
# Error: Access Denied (IAM condition blocks it)

# Terminate EC2 tagged mh:environment=prod
aws ec2 terminate-instances --instance-ids i-prod123 ❌
# Error: Access Denied (explicit Deny statement)
```

### Tag as Security Boundary

```
Resource: arn:aws:s3:::sensitive-data-bucket
Tags:
  mh:environment: prod

Developer tries: aws s3 ls s3://sensitive-data-bucket

IAM evaluates:
  1. Action: s3:ListBucket ✓ (in Allow statement)
  2. Condition: aws:ResourceTag/mh:environment != prod ✗
  3. Result: DENY
```

---

## Benefits Over Account-Based

| Scenario | Account-Based | Tag-Based |
|----------|---------------|-----------|
| Test DB in prod account | Developer blocked ❌ | Developer can access if tagged `dev` ✅ |
| Prod data in dev account | Developer has access ❌ | Developer blocked if tagged `prod` ✅ |
| Cross-account replication | Complex IAM roles needed | Tag follows the data ✅ |
| Multi-tenant applications | Need separate accounts | Single account, tag per tenant ✅ |

---

## Implementation Requirements

### 1. Resources MUST Be Tagged

**Enforcement**:
```yaml
# AWS Config rule
Resources:
  RequireEnvironmentTag:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: require-mh-environment-tag
      Source:
        Owner: AWS
        SourceIdentifier: REQUIRED_TAGS
      InputParameters:
        tag1Key: mh:environment
```

### 2. Tag Values Must Be Standardized

**Allowed values** (from STANDARDS.md):
- `dev`
- `qa`
- `stage`
- `prod`
- `sandbox`
- `unknown`

**Not allowed**:
- `production` (use `prod`)
- `development` (use `dev`)
- `test` (use `qa` or `sandbox`)

### 3. Tags Cannot Be Changed on Prod Resources

```json
{
  "Sid": "DenyProdTagChanges",
  "Effect": "Deny",
  "Action": [
    "ec2:CreateTags",
    "ec2:DeleteTags",
    "s3:PutBucketTagging"
  ],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:ResourceTag/mh:environment": "prod"
    }
  }
}
```

**Prevents**: Developer changing `mh:environment: prod` → `dev` to gain access

---

## Assignment Matrix (Updated)

```yaml
permission_sets:
  MH-Developer:
    # Assigned to ALL accounts
    accounts: all
    
    # Access controlled by resource tags, not account
    access_model: tag_based
    
    # What they can do
    allow:
      - Read all resources (metadata)
      - Write to resources tagged mh:environment != prod
      - Read logs in all environments
    
    deny:
      - Write to resources tagged mh:environment = prod
      - Delete resources tagged mh:environment = prod
      - Change tags on resources tagged mh:environment = prod
```

---

## Migration Path

**Phase 1**: Deploy tag-based policies (parallel with account-based)
- MH-Developer uses tag conditions
- Old permission sets remain unchanged
- Both work simultaneously

**Phase 2**: Validate tag coverage
```bash
# Find untagged resources
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=mh:environment \
  | jq '.ResourceTagMappingList | length'

# Target: 90%+ tagged
```

**Phase 3**: Enforce tagging via Config rules
- Auto-remediate: Add `mh:environment: unknown` to untagged resources
- Alert on `unknown` tags

**Phase 4**: Remove account-based restrictions
- All access decisions via tags
- Accounts are just organizational units

---

## Edge Cases

### Untagged Resources
**Behavior**: Denied by default (tag condition requires tag to exist)

**Options**:
1. Treat as prod (safest)
2. Treat as `unknown` (requires tagging first)
3. Allow (dangerous)

**Recommendation**: Deny untagged, auto-tag as `unknown`, alert

### Multi-Environment Resources
**Example**: S3 bucket with dev + prod data

**Solution**: Tag as most restrictive
```
mh:environment: prod  # Entire bucket restricted
mh:data-classification: mixed  # Additional context
```

**Alternative**: Separate buckets by environment

### Cross-Environment Dependencies
**Example**: Dev Lambda reads prod RDS (read-replica)

**Solution**: Grant specific exception
```json
{
  "Sid": "DevLambdaReadProdReplica",
  "Effect": "Allow",
  "Action": "rds-db:connect",
  "Resource": "arn:aws:rds:*:*:db:prod-read-replica",
  "Condition": {
    "StringEquals": {
      "aws:PrincipalTag/Project": "analytics"
    }
  }
}
```

---

## Validation Script

```bash
#!/bin/bash
# validate-tag-access.sh
# Test tag-based access control

echo "Testing MH-Developer tag-based access..."

# Should succeed (dev resource)
aws s3 ls s3://dev-bucket/ && echo "✓ Dev access works"

# Should fail (prod resource)
aws s3 ls s3://prod-bucket/ 2>&1 | grep -q "Access Denied" && echo "✓ Prod blocked"

# Should succeed (read prod metadata)
aws ec2 describe-instances --filters "Name=tag:mh:environment,Values=prod" && echo "✓ Can read prod metadata"

# Should fail (terminate prod instance)
aws ec2 terminate-instances --instance-ids i-prod123 2>&1 | grep -q "not authorized" && echo "✓ Cannot terminate prod"

echo "Validation complete"
```

---

## Decision: Use Tags

**Change to account-assignment-matrix.yaml**:

```yaml
permission_sets:
  MH-Developer:
    accounts: all  # Assign to all accounts
    access_control_method: resource_tags  # New
    environment_restrictions:
      # Remove account-based restrictions
      # Add tag-based restrictions (in IAM policy conditions)
```

**Simplification**:
- No need to track "which accounts are prod"
- No need to update matrix when account classification changes
- Resources define their own sensitivity via tags
