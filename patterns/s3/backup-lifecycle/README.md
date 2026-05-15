# S3 Backup Lifecycle Pattern

Reusable CloudFormation pattern for cost-optimized backup retention across S3 buckets.

## Purpose

Automate backup lifecycle management to reduce storage costs while maintaining compliance.

**Example savings:** EDW backups reduced from $79K/year → $4K/year (95% reduction)

## Features

- Tag-based retention (Weekly vs Monthly)
- Automatic storage tiering (Standard → IA → Glacier)
- Configurable retention periods
- Cost-optimized for different backup profiles

## Quick Deploy - EDW Example

```bash
cd cloudformation

aws cloudformation create-stack \
  --stack-name edw-backup-lifecycle \
  --template-body file://backup-lifecycle-stack.yaml \
  --parameters \
    ParameterKey=BackupBucketName,ParameterValue=mh-edw-backup \
    ParameterKey=WeeklyRetentionDays,ParameterValue=90 \
    ParameterKey=MonthlyRetentionDays,ParameterValue=395 \
  --profile mh-ops \
  --region us-east-1
```

## Components

### CloudFormation Templates
- **backup-lifecycle-stack.yaml** - Reusable module with 3 lifecycle rules
- **edw-backup-stack.yaml** - EDW-specific implementation (13-month retention)

### Scripts
- **Upload-Backup-To-S3.ps1** - Generic PowerShell upload script with auto-tagging
- **EDW-Backup-Upload.xml** - Task Scheduler configuration

### Documentation
- **governance.md** - Standard retention policies (30d, 90d, 13mo, 7yr)
- **deployment-guide.md** - Step-by-step deployment instructions

## Standard Retention Policies

| Policy | Use Case | Weekly Retention | Monthly Retention | Annual Cost (per TB) |
|--------|----------|------------------|-------------------|---------------------|
| **A: Short-Term** | Dev/staging | 30 days | None | ~$18/TB |
| **B: Standard** | Production DBs | 90 days | None | ~$10/TB |
| **C: Compliance** | Data warehouses | 90 days | 13 months | ~$8/TB |
| **D: Long-Term** | Regulatory | 90 days | 7 years | ~$3/TB |

## Tagging Requirements

Upload scripts must tag objects for proper lifecycle routing:

```powershell
# Weekly backup (90-day retention)
aws s3 cp file.bak s3://bucket/ --tagging "Retention=Weekly"

# Monthly backup (13-month retention)
aws s3 cp file.bak s3://bucket/ --tagging "Retention=Monthly"
```

The PowerShell script auto-detects first week of month for monthly backups.

## Architecture

```
Upload Script → S3 Bucket → Lifecycle Policy
                               ├─ Weekly: Standard → IA → Glacier → Delete (90d)
                               └─ Monthly: Glacier → Delete (395d)
```

## Related Patterns

- [IAM patterns](../../iam/) - S3 bucket policies
- [Lambda patterns](../../lambda/) - Event-driven automation
- [StackSets](../../stacksets/) - Multi-account deployment

## Support

Questions? Contact Platform Engineering or see [COSE repo README](../../../README.md).
