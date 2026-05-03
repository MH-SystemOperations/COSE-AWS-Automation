# WorkSpaces Lifecycle Automation

Automatically detect and delete unused WorkSpaces to prevent cost waste.

## Problem

WorkSpaces accumulate over time when users provision them, never use them, and forget they exist. Manual quarterly audits are time-consuming and reactive.

**Cost impact:** $1,500-2,000/mo waste from 365+ day unused WorkSpaces

## Solution

Automated lifecycle management with safety guardrails:
1. Weekly scan detects 90+ days zero usage
2. Email warning sent to user (14-day notice)
3. Re-check usage before deletion (abort if used)
4. Create backup image (90-day retention)
5. Terminate WorkSpace
6. Clean up image after 90 days

## Safety Mechanisms

**Multiple verification checks:**
- Initial 90-day usage check
- 14-day re-check before deletion
- Manual abort via DynamoDB KeepAlive flag

**Exclusions:**
- Shared accounts (CAR-XX, cmh-XX, LAI-XX)
- WorkSpaces marked as KeepAlive
- Configurable regex patterns in SSM

**Audit trail:**
- DynamoDB tracks every action with timestamps
- Backup images retained 90 days
- Can restore WorkSpace within 90 days

**DRY_RUN mode:**
- Enabled by default
- Logs actions without making changes
- Test before enabling real mode

## Architecture

**Management Account:**
- Lambda: WorkSpacesLifecycleManager (weekly scan)
- Lambda: ImageCleanup (daily cleanup)
- DynamoDB: WorkSpacesLifecycleTracking (audit trail)
- SNS: Notifications
- EventBridge: Schedules

**All Accounts (via StackSet):**
- IAM Role: WorkSpacesLifecycleRole
- Permissions: Describe, Terminate, CreateImage, CloudWatch metrics

## Deployment

### Prerequisites
- AWS CLI configured with mh-ops profile
- Permissions to deploy CloudFormation in management account
- Organizations API access

### Step 1: Deploy cross-account roles
```bash
aws cloudformation create-stack-set \
  --stack-set-name WorkSpacesLifecycleRoles \
  --template-body file://cfn/cross-account-role.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile mh-ops \
  --region us-east-1

# Deploy to accounts
aws cloudformation create-stack-instances \
  --stack-set-name WorkSpacesLifecycleRoles \
  --accounts 266565038828 971318514578 480202104756 \
  --regions us-east-1 \
  --profile mh-ops
```

### Step 2: Deploy orchestrator (management account)
```bash
aws cloudformation create-stack \
  --stack-name WorkSpacesLifecycleOrchestrator \
  --template-body file://cfn/orchestrator.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=DryRunMode,ParameterValue=true \
  --profile mh-ops \
  --region us-east-1
```

### Step 3: Deploy Lambda code
```bash
# Package Lambda functions
cd lambda
zip -r lifecycle_manager.zip lifecycle_manager.py
zip -r image_cleanup.zip image_cleanup.py

# Update Lambda functions
aws lambda update-function-code \
  --function-name WorkSpacesLifecycleManager \
  --zip-file fileb://lifecycle_manager.zip \
  --profile mh-ops \
  --region us-east-1

aws lambda update-function-code \
  --function-name WorkSpacesImageCleanup \
  --zip-file fileb://image_cleanup.zip \
  --profile mh-ops \
  --region us-east-1
```

### Step 4: Test in dry-run mode
```bash
# Manually invoke Lambda
aws lambda invoke \
  --function-name WorkSpacesLifecycleManager \
  --payload '{}' \
  --profile mh-ops \
  --region us-east-1 \
  response.json

# Check CloudWatch Logs
aws logs tail /aws/lambda/WorkSpacesLifecycleManager --follow --profile mh-ops
```

### Step 5: Enable real mode (after testing)
```bash
aws cloudformation update-stack \
  --stack-name WorkSpacesLifecycleOrchestrator \
  --use-previous-template \
  --parameters \
    ParameterKey=DryRunMode,ParameterValue=false \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile mh-ops \
  --region us-east-1
```

## Configuration

**SSM Parameters:**
- `/workspaces/lifecycle/accounts-to-scan` - Comma-separated account IDs
- `/workspaces/lifecycle/excluded-users` - Regex patterns (CAR-.*, cmh-.*, LAI-.*)

**CloudFormation Parameters:**
- `DryRunMode` - true/false (default: true)
- `UnusedThresholdDays` - Days before warning (default: 90)
- `WarningPeriodDays` - Days between warning and deletion (default: 14)

## Manual Intervention

**Abort a pending deletion:**
```bash
aws dynamodb update-item \
  --table-name WorkSpacesLifecycleTracking \
  --key '{"WorkspaceId": {"S": "ws-xxxxx"}}' \
  --update-expression "SET #status = :status" \
  --expression-attribute-names '{"#status": "Status"}' \
  --expression-attribute-values '{":status": {"S": "KeepAlive"}}' \
  --profile mh-ops \
  --region us-east-1
```

**Restore a deleted WorkSpace:**
```bash
# 1. Get image ID from DynamoDB
aws dynamodb get-item \
  --table-name WorkSpacesLifecycleTracking \
  --key '{"WorkspaceId": {"S": "ws-xxxxx"}}' \
  --profile mh-ops

# 2. Recreate WorkSpace from image
aws workspaces create-workspaces \
  --workspaces file://restore.json \
  --profile <account-profile> \
  --region us-east-1
```

## Monitoring

**CloudWatch Metrics:**
- Lambda invocations, errors, duration
- DynamoDB read/write capacity

**DynamoDB Queries:**
```bash
# List pending deletions
aws dynamodb scan \
  --table-name WorkSpacesLifecycleTracking \
  --filter-expression "#status = :status" \
  --expression-attribute-names '{"#status": "Status"}' \
  --expression-attribute-values '{":status": {"S": "WarningPending"}}' \
  --profile mh-ops

# List deleted WorkSpaces
aws dynamodb scan \
  --table-name WorkSpacesLifecycleTracking \
  --filter-expression "#status = :status" \
  --expression-attribute-names '{"#status": "Status"}' \
  --expression-attribute-values '{":status": {"S": "Deleted"}}' \
  --profile mh-ops
```

## Testing Strategy

**Week 1: Dry-run**
- Deploy with DRY_RUN=true
- Verify correct WorkSpaces identified
- Check exclusion patterns work

**Week 2: Single account**
- Enable for data-prod only
- Monitor full 14-day cycle
- Test manual abort

**Week 3+: Org-wide**
- Enable for all accounts
- Monitor for false positives

## Rollback

**Disable automation:**
```bash
aws events disable-rule --name WorkSpacesLifecycleWeeklyScan --profile mh-ops
aws events disable-rule --name WorkSpacesImageDailyCleanup --profile mh-ops
```

**Delete stack:**
```bash
aws cloudformation delete-stack --stack-name WorkSpacesLifecycleOrchestrator --profile mh-ops
```

## Success Metrics

- Zero false positive deletions
- $1,500-2,000/mo savings maintained
- 100% audit trail in DynamoDB
- <5 min response time for manual aborts

## Files

- `cfn/orchestrator.yaml` - Main CloudFormation stack
- `cfn/cross-account-role.yaml` - StackSet for IAM roles
- `lambda/lifecycle_manager.py` - Main lifecycle logic
- `lambda/image_cleanup.py` - Image cleanup logic
- `tests/` - Unit and integration tests
