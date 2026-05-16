# Apply S3 Lifecycle Rules to Existing Bucket (CLI Method)

## Why CLI Instead of CloudFormation?

**CloudFormation limitation:** The `AWS::S3::Bucket` resource type **creates** a bucket. It cannot apply lifecycle rules to an existing bucket without:
1. Importing the bucket into CloudFormation (complex, risky)
2. Using a Custom Resource with Lambda (overkill for one-time setup)

**Solution:** Use AWS CLI to apply lifecycle rules directly to existing bucket.

---

## Current State in AWS (as of May 16, 2026)

**Bucket:** `mh-edw-backup` (exists, managed outside CloudFormation)

**Lifecycle rules currently applied:**

```json
{
  "Rules": [
    {
      "ID": "WeeklyBackupRetention",
      "Status": "Enabled",
      "Filter": {
        "Tag": {"Key": "Retention", "Value": "Weekly"}
      },
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 60, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 90}
    },
    {
      "ID": "MonthlyBackupRetention",
      "Status": "Enabled",
      "Filter": {
        "Tag": {"Key": "Retention", "Value": "Monthly"}
      },
      "Transitions": [
        {"Days": 1, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 395}
    },
    {
      "ID": "DefaultBackupRetention",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 60, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 90},
      "NoncurrentVersionExpiration": {"NoncurrentDays": 1}
    }
  ]
}
```

---

## Issues with Current Configuration

### 🚨 Issue #1: Glacier 90-Day Minimum Storage Duration

**Problem:** Weekly backups transition to Glacier at day 60, delete at day 90 = **30 days in Glacier**.

**AWS Charges:** Glacier has a **90-day minimum storage duration**. Deleting before 90 days incurs **early deletion charges** as if the object stayed the full 90 days.

**Cost impact:**
- Weekly backup size: ~800 GB per backup × 4 weeks = 3.2 TB
- Early deletion cost: 3.2 TB × $0.004/GB × (90-30 days prorated) ≈ **extra $8.50/month**
- Small but avoidable

**Solutions:**
1. **Option A (Recommended):** Remove Glacier transition for weekly backups - keep in STANDARD_IA until deletion
2. **Option B:** Change weekly retention to 150 days (60 + 90 = keeps in Glacier for full 90 days minimum)

---

### 🚨 Issue #2: Catch-All Rule Uses Prefix Filter (Safe)

**Copilot warned:** Default rule with `Prefix: ''` might conflict with tagged rules.

**Reality:** AWS S3 lifecycle evaluation is **most-specific-first**:
1. Tagged objects match tag-filtered rules first (Weekly/Monthly)
2. Untagged objects fall through to prefix-based default rule
3. **No conflict** - this design is correct

---

### 📝 Issue #3: Objects Have No Tags Yet

**Current state:**
```bash
aws s3api get-object-tagging \
  --bucket mh-edw-backup \
  --key "Athena_01-03-2026.bak" \
  --profile mh-ops
# Result: TagSet: []
```

**All objects are untagged** → Using default 90-day retention

**Action needed:** Jeff needs to tag backups during upload (see scripts below)

---

## Corrected Lifecycle Configuration (Fix Glacier Issue)

### Option A: No Glacier for Weekly (Recommended)

```json
{
  "Rules": [
    {
      "ID": "WeeklyBackupRetention",
      "Status": "Enabled",
      "Filter": {
        "Tag": {"Key": "Retention", "Value": "Weekly"}
      },
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"}
      ],
      "Expiration": {"Days": 90}
    },
    {
      "ID": "MonthlyBackupRetention",
      "Status": "Enabled",
      "Filter": {
        "Tag": {"Key": "Retention", "Value": "Monthly"}
      },
      "Transitions": [
        {"Days": 1, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 395}
    },
    {
      "ID": "DefaultBackupRetention",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"}
      ],
      "Expiration": {"Days": 90},
      "NoncurrentVersionExpiration": {"NoncurrentDays": 1}
    }
  ]
}
```

**Apply this configuration:**
```bash
# Save JSON to file
cat > edw-lifecycle-rules-corrected.json << 'EOF'
{
  "Rules": [
    {
      "ID": "WeeklyBackupRetention",
      "Status": "Enabled",
      "Filter": {
        "Tag": {"Key": "Retention", "Value": "Weekly"}
      },
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"}
      ],
      "Expiration": {"Days": 90}
    },
    {
      "ID": "MonthlyBackupRetention",
      "Status": "Enabled",
      "Filter": {
        "Tag": {"Key": "Retention", "Value": "Monthly"}
      },
      "Transitions": [
        {"Days": 1, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 395}
    },
    {
      "ID": "DefaultBackupRetention",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"}
      ],
      "Expiration": {"Days": 90},
      "NoncurrentVersionExpiration": {"NoncurrentDays": 1}
    }
  ]
}
EOF

# Apply to bucket
aws s3api put-bucket-lifecycle-configuration \
  --bucket mh-edw-backup \
  --lifecycle-configuration file://edw-lifecycle-rules-corrected.json \
  --profile mh-ops
```

---

### Option B: Extended Weekly Retention (150 days)

Keep Glacier transition but extend retention to meet 90-day minimum:

```json
{
  "Rules": [
    {
      "ID": "WeeklyBackupRetention",
      "Status": "Enabled",
      "Filter": {
        "Tag": {"Key": "Retention", "Value": "Weekly"}
      },
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 60, "StorageClass": "GLACIER"}
      ],
      "Expiration": {"Days": 150}
    },
    ...
  ]
}
```

**Cost impact:** Keeps 1-2 extra weekly backups (~1.6 TB) in Glacier for extra 60 days.

---

## Upload Scripts (Fixed)

### Issue: `aws s3 cp --tagging` Does Not Exist

**Copilot was correct:** The high-level `aws s3 cp` command does **not** support `--tagging`.

**Solutions:**

#### Method 1: Two-step (Upload + Tag)

```powershell
# Upload file
aws s3 cp $file.FullName "s3://mh-edw-backup/$($file.Name)" --profile mh-ops

# Tag after upload
aws s3api put-object-tagging `
  --bucket mh-edw-backup `
  --key $file.Name `
  --tagging "TagSet=[{Key=Retention,Value=Weekly}]" `
  --profile mh-ops
```

#### Method 2: Use s3api put-object

```powershell
aws s3api put-object `
  --bucket mh-edw-backup `
  --key $file.Name `
  --body $file.FullName `
  --tagging "Retention=Weekly" `
  --profile mh-ops
```

**Recommended:** Method 1 (s3 cp + put-object-tagging) - better for large files with multipart upload

---

## CloudWatch Metrics Fix

### Issue: Dimension Format Wrong

**Current (WRONG):**
```powershell
--dimensions "Server=$MetricDimension"
```

**Correct:**
```powershell
--dimensions Name=Server,Value=$MetricDimension
```

**Fixed function:**
```powershell
function Send-CloudWatchMetric {
    param(
        [string]$MetricName,
        [double]$Value,
        [string]$Unit = 'Count'
    )

    aws cloudwatch put-metric-data `
        --namespace "EDW/Backup" `
        --metric-name "$MetricName" `
        --value $Value `
        --unit $Unit `
        --dimensions Name=Server,Value=$env:COMPUTERNAME `
        --profile mh-ops
}
```

---

## Bucket Access Check Fix

### Issue: `aws s3 ls --max-items` Does Not Exist

**Current (WRONG):**
```powershell
aws s3 ls "s3://$bucketName" --max-items 1
```

**Correct options:**

#### Option 1: Use s3api head-bucket
```powershell
function Test-BucketAccess {
    param([string]$Bucket)
    
    try {
        $bucketName = $Bucket -replace '^s3://', ''
        aws s3api head-bucket --bucket $bucketName --profile mh-ops 2>&1 | Out-Null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}
```

#### Option 2: Use s3 ls without --max-items
```powershell
aws s3 ls "s3://$bucketName" --profile mh-ops 2>&1 | Out-Null
return $LASTEXITCODE -eq 0
```

---

## Summary of Fixes Needed

### 1. Update lifecycle rules (apply via CLI)
```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket mh-edw-backup \
  --lifecycle-configuration file://edw-lifecycle-rules-corrected.json \
  --profile mh-ops
```

### 2. Fix PowerShell upload script
- Replace `aws s3 cp --tagging` with two-step upload+tag
- Fix CloudWatch dimensions format
- Fix bucket access check (remove --max-items)

### 3. Update documentation
- Document that CloudFormation templates are **reference implementations**
- They show the lifecycle configuration but don't deploy it
- Actual deployment is via AWS CLI for existing buckets

### 4. Clarify in README
- Note the Glacier 90-day minimum issue
- Recommend Option A (no Glacier for weekly)
- Document that objects need tags to use tag-based rules

---

## Why Not Fix the CloudFormation Templates?

**CloudFormation can't manage existing buckets without import.**

**Options:**
1. **Import bucket into CloudFormation** - Complex, risky, requires precise configuration match
2. **Custom Resource with Lambda** - Overkill for one-time setup
3. **Delete and recreate bucket** - VERY BAD (data loss)
4. **Use CLI** - Simple, direct, works immediately ✅

**Decision:** Keep CloudFormation templates as **documentation/reference**, use CLI for actual deployment.

---

## Next Steps

1. Apply corrected lifecycle rules via CLI (Option A recommended)
2. Update PowerShell script with fixes above
3. Test upload with tagging
4. Verify CloudWatch metrics publish correctly
5. Update PR with this document + fixes
