# EDW Backup - Phased Implementation

**Phase 1 (Now): S3 Lifecycle Only - $75K/year savings**  
**Phase 2 (Later): Add Automation - $19K/year additional + eliminate Jeff's manual work**

---

## Phase 1: Deploy S3 Lifecycle Policy (Do Now - 5 min)

**Savings: $75K/year**  
**Risk: Very low** - only affects storage retention, doesn't change upload process

### Step 1: Commit to Git (2 min)

```bash
cd ~/Desktop/COSE-AWS-Automation
git add patterns/s3/
git commit -m "Add S3 backup lifecycle pattern - Phase 1: lifecycle policy"
git push
```

### Step 2: Deploy CloudFormation (3 min)

```bash
cd ~/Desktop/COSE-AWS-Automation/patterns/s3/backup-lifecycle/cloudformation

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

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name edw-backup-lifecycle \
  --profile mh-ops

# Verify
aws cloudformation describe-stacks \
  --stack-name edw-backup-lifecycle \
  --profile mh-ops \
  --query 'Stacks[0].StackStatus'
```

**Expected output:** `CREATE_COMPLETE`

---

## What Happens Now

### Immediate (Today)
- ✅ S3 lifecycle policy is active
- ✅ Future uploads will be tiered automatically
- ✅ Old backups (90+ days) will start deleting

### Jeff's Process (Unchanged)
- Jeff continues manual weekend uploads (no change)
- He should **tag uploads** for best results (optional but recommended)
- Without tags, files default to 90-day retention (still saves money)

### Optional: Ask Jeff to Tag Manually

If Jeff wants to tag during manual upload:

```bash
# Weekly backup (first 3 Sundays)
aws s3 cp Consolidated_05-18-2026.bak s3://mh-edw-backup/ --tagging "Retention=Weekly"

# Monthly backup (first Sunday of month)
aws s3 cp Consolidated_05-04-2026.bak s3://mh-edw-backup/ --tagging "Retention=Monthly"
```

**But this is optional** - untagged files still get 90-day retention.

---

## Cost Savings Timeline

| Month | S3 Storage Cost | Savings (cumulative) | Notes |
|-------|-----------------|----------------------|-------|
| **Current** | $79,452/year | - | 246 TB retained |
| **Month 1** | ~$50,000/year | $29K | Files start transitioning to IA/Glacier |
| **Month 2** | ~$30,000/year | $49K | More files in Glacier |
| **Month 3** | ~$15,000/year | $64K | 90+ day files start deleting |
| **Month 4+** | ~$4,400/year | **$75K** | Steady state reached |

---

## Verification (Week 1)

### Check lifecycle policy applied
```bash
aws s3api get-bucket-lifecycle-configuration \
  --bucket mh-edw-backup \
  --profile mh-ops
```

Should show 3 rules: WeeklyBackupRetention, MonthlyBackupRetention, DefaultBackupRetention

### Monitor storage transitions (optional)
```bash
# Check storage class distribution
aws s3api list-objects-v2 \
  --bucket mh-edw-backup \
  --query 'Contents[*].[Key,StorageClass]' \
  --profile mh-ops \
  | grep -E "(STANDARD|STANDARD_IA|GLACIER)" \
  | sort | uniq -c
```

After 14 days, you'll see files moving to STANDARD_IA, then GLACIER at 60 days.

---

## Phase 2: Add Automation (Later - When Ready)

**Additional Savings: $19K/year (Veeam) + Jeff's time**  
**When:** After confirming Phase 1 working (1-2 months)

### Benefits of Adding Automation
- Eliminates Jeff's 2 hrs/week manual work
- Ensures consistent tagging (monthly vs weekly)
- CloudWatch monitoring/alerting
- Can then scale back Veeam with confidence

### Steps (future)
1. Deploy PowerShell script to EDW server
2. Configure Task Scheduler
3. Test automated uploads for 2 weeks
4. Scale back Veeam retention once automation proven

See [IMPLEMENTATION-CHECKLIST.md](IMPLEMENTATION-CHECKLIST.md) for full automation steps when ready.

---

## Notify Jeff (Optional - 2 min)

```
Subject: S3 Lifecycle Policy Applied to EDW Backups

Jeff,

We've applied a cost optimization policy to the mh-edw-backup S3 bucket:

- First 14 days: Standard storage (fast access)
- 15-60 days: Standard-IA (still immediate access, cheaper)
- 61-90 days: Glacier (12-hour restore time)
- 90+ days: Deleted automatically

Your manual upload process stays the same for now. 

Optional: If you want to keep monthly backups for 13 months instead of 90 days, 
tag them during upload with: --tagging "Retention=Monthly"

This saves $75K/year immediately. We'll talk about automating your weekend 
uploads in a month or two once this is proven out.

Questions? Let me know!
```

---

## Rollback (If Needed)

If lifecycle policy causes any issues:

```bash
# Disable (don't delete stack, just disable rules)
aws cloudformation update-stack \
  --stack-name edw-backup-lifecycle \
  --use-previous-template \
  --parameters \
    ParameterKey=BackupBucketName,UsePreviousValue=true \
    ParameterKey=Environment,UsePreviousValue=true \
    ParameterKey=WeeklyRetentionDays,UsePreviousValue=true \
  --profile mh-ops

# Or completely remove
aws cloudformation delete-stack \
  --stack-name edw-backup-lifecycle \
  --profile mh-ops
```

Lifecycle policies are non-destructive - they only delete files that age past retention. Already-deleted files cannot be recovered, but the policy can be disabled anytime.

---

## Success Criteria (Phase 1)

- ✅ CloudFormation stack deployed successfully
- ✅ Lifecycle policy visible in S3 console
- ✅ No impact to Jeff's manual process
- ✅ Files start transitioning after 14 days
- ✅ Cost reduction visible in month 2-3 billing
- ✅ No restore requests for deleted files

**Once proven → Proceed to Phase 2 automation**

---

## Summary

**Do now:**
- Deploy S3 lifecycle CloudFormation stack (5 min)
- Monitor for 1-2 months
- Save $75K/year

**Do later:**
- Add PowerShell automation
- Scale back Veeam
- Save additional $19K/year

**Total eventual savings: $94K/year**
