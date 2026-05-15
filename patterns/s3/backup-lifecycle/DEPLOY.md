# EDW Backup - Quick Deploy

**Savings: $94K/year** ($118K → $24K)

## Step 1: Deploy CloudFormation (5 min)

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

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name edw-backup-lifecycle \
  --profile mh-ops
```

**Result:** S3 lifecycle active, $75K/year saved

## Step 2: Deploy Script to EDW (10 min)

```powershell
# On E1A-EDW-01
cd C:\Scripts
git clone https://github.com/MH-SystemOperations/COSE-AWS-Automation.git

Copy-Item COSE-AWS-Automation\patterns\s3\backup-lifecycle\scripts\Upload-Backup-To-S3.ps1 -Destination C:\Scripts\

# Test
.\Upload-Backup-To-S3.ps1 -WhatIf
```

## Step 3: Configure Scheduler (5 min)

```powershell
schtasks /Create /XML "C:\Scripts\COSE-AWS-Automation\patterns\s3\backup-lifecycle\scripts\EDW-Backup-Upload.xml" /TN "EDW Backup Upload"
```

**Result:** Automated weekly uploads, Jeff's manual work eliminated

## Step 4: Scale Back Veeam (5 min)

In Veeam console:
- Daily: 14d → 7d
- Monthly: 12m → 3m
- Yearly: 7y → 0

**Result:** $19K/year additional savings

## Total Impact

- Cost: $118K → $24K/year
- Savings: $94K/year
- Time: 25 minutes
