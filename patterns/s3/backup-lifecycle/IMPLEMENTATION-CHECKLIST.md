# EDW Backup Optimization - Implementation Checklist

**Total Time: 30 minutes**  
**Total Savings: $94,000/year**

---

## Pre-Implementation Checks

- [ ] Confirm EDW backup bucket name: `mh-edw-backup`
- [ ] Confirm EDW server name: `E1A-EDW-01`
- [ ] Confirm backup path: `I:\Backup` (adjust in scripts if different)
- [ ] AWS CLI configured with `mh-ops` profile
- [ ] Access to Veeam console
- [ ] Coordinate with Jeff (current manual process will stop)

---

## Phase 1: Apply S3 Lifecycle Policy (5 min)

**Savings: $75K/year**

```bash
cd ~/Desktop/COSE-AWS-Automation/patterns/s3/backup-lifecycle/cloudformation

# Validate template
aws cloudformation validate-template \
  --template-body file://backup-lifecycle-stack.yaml \
  --profile mh-ops

# Deploy
aws cloudformation create-stack \
  --stack-name edw-backup-lifecycle \
  --template-body file://backup-lifecycle-stack.yaml \
  --parameters \
    ParameterKey=BackupBucketName,ParameterValue=mh-edw-backup \
    ParameterKey=Environment,ParameterValue=Production \
    ParameterKey=WeeklyRetentionDays,ParameterValue=90 \
    ParameterKey=WeeklyToIADays,ParameterValue=14 \
    ParameterKey=WeeklyToGlacierDays,ParameterValue=60 \
    ParameterKey=MonthlyRetentionDays,ParameterValue=395 \
    ParameterKey=MonthlyToGlacierDays,ParameterValue=1 \
  --region us-east-1 \
  --profile mh-ops

# Wait for completion (2-3 minutes)
aws cloudformation wait stack-create-complete \
  --stack-name edw-backup-lifecycle \
  --profile mh-ops

# Verify
aws cloudformation describe-stacks \
  --stack-name edw-backup-lifecycle \
  --profile mh-ops \
  --query 'Stacks[0].StackStatus'
```

**Verification:**
- [ ] Stack status: `CREATE_COMPLETE`
- [ ] S3 bucket lifecycle rules visible in AWS console
- [ ] No errors in CloudFormation events

---

## Phase 2: Deploy Automation Script to EDW (10 min)

**Savings: Jeff's 2 hrs/week**

### On your workstation:
```bash
# Push COSE repo if not already done
cd ~/Desktop/COSE-AWS-Automation
git add patterns/s3/
git commit -m "Add S3 backup lifecycle pattern - saves $94K/year"
git push
```

### On EDW server (E1A-EDW-01):
```powershell
# Create directories
New-Item -Path "C:\Scripts" -ItemType Directory -Force
New-Item -Path "C:\Scripts\Logs" -ItemType Directory -Force

# Clone or pull COSE repo
cd C:\Scripts
git clone https://github.com/MH-SystemOperations/COSE-AWS-Automation.git
# Or if already exists: cd COSE-AWS-Automation && git pull

# Copy script to working directory
Copy-Item "C:\Scripts\COSE-AWS-Automation\patterns\s3\backup-lifecycle\scripts\Upload-Backup-To-S3.ps1" `
  -Destination "C:\Scripts\Upload-Backup-To-S3.ps1"

# Test (WhatIf mode - no changes)
cd C:\Scripts
.\Upload-Backup-To-S3.ps1 -WhatIf

# Review test output
Get-Content "C:\Scripts\Logs\backup-upload-$(Get-Date -Format 'yyyy-MM-dd').log"
```

**Verification:**
- [ ] Script runs without errors in WhatIf mode
- [ ] Log file created in C:\Scripts\Logs\
- [ ] Script found .bak files (if backups exist)
- [ ] AWS credentials working

---

## Phase 3: Configure Task Scheduler (5 min)

```powershell
# On E1A-EDW-01
# Import pre-configured task
schtasks /Create /XML "C:\Scripts\COSE-AWS-Automation\patterns\s3\backup-lifecycle\scripts\EDW-Backup-Upload.xml" /TN "EDW Backup Upload"

# Verify task created
schtasks /Query /TN "EDW Backup Upload" /V /FO LIST

# Test manual run (actual upload)
schtasks /Run /TN "EDW Backup Upload"

# Check results
Get-Content "C:\Scripts\Logs\backup-upload-$(Get-Date -Format 'yyyy-MM-dd').log" -Tail 50

# Verify in S3
aws s3 ls s3://mh-edw-backup/ --profile mh-ops | Select-String "$(Get-Date -Format 'MM-dd-yyyy')"
```

**Verification:**
- [ ] Task Scheduler entry exists
- [ ] Task runs successfully
- [ ] Files uploaded to S3
- [ ] Object tags applied correctly (check one file in S3 console)
- [ ] Local .bak files deleted after upload

---

## Phase 4: Scale Back Veeam (5 min)

**Savings: $19K/year**

### In Veeam Backup & Replication console:

1. Find EDW backup job
2. Edit job settings → Storage → Retention Policy:
   - **Daily backups:** Change from 14 to **7** restore points
   - **Monthly backups:** Change from 12 to **3** restore points
   - **Yearly backups:** Change from 7 to **0** (disable)
3. Save changes
4. Run manual cleanup: Right-click job → "Remove deleted VMs data"

**Verification:**
- [ ] Retention settings updated
- [ ] Old backup files queued for deletion
- [ ] Monitor Veeam storage reduction over next week

---

## Phase 5: Notify Jeff (2 min)

```
Subject: EDW Backup Automation Deployed - Your Manual Work is Done!

Jeff,

Good news - EDW backup automation is now live:

✅ Weekly .bak files automatically upload to S3 every Sunday at 8 AM
✅ First Sunday of month = monthly backup (13-month retention)
✅ You no longer need to manually upload on weekends!

The system will:
- Upload .bak files after SSIS completes
- Tag them for proper retention (weekly vs monthly)
- Delete local copies after successful upload
- Alert if uploads fail

Savings: $94K/year + your 2 hrs/week

If you see any issues, check: C:\Scripts\Logs\ on E1A-EDW-01

Thanks for the collaboration!
```

---

## Post-Implementation Monitoring

### Week 1
- [ ] Check logs daily: `C:\Scripts\Logs\backup-upload-*.log`
- [ ] Verify S3 uploads happening
- [ ] Confirm local .bak files being deleted
- [ ] No Task Scheduler failures

### Week 4 (First Monthly)
- [ ] Verify first Sunday upload gets `Retention=Monthly` tag
- [ ] Check S3 console: Object → Properties → Tags
- [ ] Confirm monthly backup moves to Glacier next day

### Month 3
- [ ] Check AWS Cost Explorer for S3 storage reduction
- [ ] Expected: $79K → ~$20K → ~$10K → ~$4K (steady state at month 4)
- [ ] Verify old backups (90+ days) are being deleted

### Month 6
- [ ] Review Snowflake migration timeline
- [ ] Plan EDW decommissioning

---

## Rollback Procedure (If Needed)

### Disable S3 Lifecycle
```bash
aws cloudformation delete-stack \
  --stack-name edw-backup-lifecycle \
  --profile mh-ops
```

### Disable Task Scheduler
```powershell
schtasks /Change /TN "EDW Backup Upload" /DISABLE
```

### Re-enable Manual Process
- Jeff resumes manual weekend uploads

---

## Success Metrics

- ✅ S3 lifecycle policy active
- ✅ Automated uploads working weekly
- ✅ Jeff's manual work eliminated
- ✅ Veeam retention reduced
- ✅ No backup failures for 4 weeks
- ✅ Cost reduction visible in billing (month 3+)

**Total annual savings: $94,000**

---

## Support

Issues? Contact:
- Platform Engineering team
- Review logs: `C:\Scripts\Logs\` on EDW server
- Check CloudFormation events in AWS console
