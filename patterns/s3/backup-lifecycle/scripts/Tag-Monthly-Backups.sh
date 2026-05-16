#!/bin/bash
# Automatically tag the latest backup of each month for 13-month retention
# This should run monthly to maintain rolling 13-month monthly backup retention

set -e

BUCKET="${1:-mh-edw-backup}"
PROFILE="${2:-mh-ops}"
MONTHS_TO_KEEP="${3:-13}"
FILE_PATTERN="${4:-Consolidated}"

echo "==========================================="
echo "Monthly Backup Tagging Script"
echo "==========================================="
echo "Bucket: $BUCKET"
echo "Profile: $PROFILE"
echo "Pattern: $FILE_PATTERN*.bak"
echo "Months to keep: $MONTHS_TO_KEEP"
echo ""

# Get all matching backup files with their last modified dates
echo "Step 1: Finding all backup files matching pattern..."
FILES=$(aws s3api list-objects-v2 \
  --bucket "$BUCKET" \
  --profile "$PROFILE" \
  --query "Contents[?contains(Key, '$FILE_PATTERN') && contains(Key, '.bak')].[Key,LastModified]" \
  --output text)

if [ -z "$FILES" ]; then
    echo "ERROR: No files found matching pattern: $FILE_PATTERN"
    exit 1
fi

echo "Found $(echo "$FILES" | wc -l) backup files"
echo ""

# Group by month and find latest in each month
echo "Step 2: Identifying latest backup per month..."
declare -A MONTHLY_BACKUPS

while IFS=$'\t' read -r key modified; do
    # Extract year-month from LastModified (format: YYYY-MM-DDTHH:MM:SS+00:00)
    year_month=$(echo "$modified" | cut -d'T' -f1 | cut -d'-' -f1,2)

    # Convert to timestamp for comparison
    timestamp=$(date -d "$modified" +%s 2>/dev/null || echo 0)

    # If this is the first file for this month, or newer than existing
    current_timestamp=${MONTHLY_BACKUPS[$year_month]##*:}
    if [ -z "$current_timestamp" ] || [ "$timestamp" -gt "$current_timestamp" ]; then
        MONTHLY_BACKUPS[$year_month]="$key:$timestamp"
    fi
done <<< "$FILES"

# Calculate cutoff date (13 months ago)
CUTOFF_DATE=$(date -d "$MONTHS_TO_KEEP months ago" +%Y-%m)

# Filter to only keep last N months
FILTERED_BACKUPS=()
for year_month in $(echo "${!MONTHLY_BACKUPS[@]}" | tr ' ' '\n' | sort -r); do
    if [[ "$year_month" > "$CUTOFF_DATE" ]] || [[ "$year_month" == "$CUTOFF_DATE" ]]; then
        backup_key=${MONTHLY_BACKUPS[$year_month]%%:*}
        FILTERED_BACKUPS+=("$year_month:$backup_key")
    fi
done

if [ ${#FILTERED_BACKUPS[@]} -eq 0 ]; then
    echo "WARNING: No backups found in the last $MONTHS_TO_KEEP months"
    exit 0
fi

echo "Found ${#FILTERED_BACKUPS[@]} monthly backups to tag:"
for entry in "${FILTERED_BACKUPS[@]}"; do
    month=${entry%%:*}
    file=${entry#*:}
    echo "  $month: $file"
done
echo ""

# Tag each monthly backup
echo "Step 3: Tagging monthly backups..."
SUCCESS=0
FAILED=0

for entry in "${FILTERED_BACKUPS[@]}"; do
    file=${entry#*:}

    echo -n "Tagging: $file ... "

    # Check if already tagged
    EXISTING_TAGS=$(aws s3api get-object-tagging \
      --bucket "$BUCKET" \
      --key "$file" \
      --profile "$PROFILE" \
      --output text 2>/dev/null || echo "")

    if echo "$EXISTING_TAGS" | grep -q "Retention.*Monthly"; then
        echo "✓ Already tagged (skipped)"
        ((SUCCESS++))
        continue
    fi

    # Apply Monthly retention tag
    aws s3api put-object-tagging \
      --bucket "$BUCKET" \
      --key "$file" \
      --tagging "TagSet=[{Key=Retention,Value=Monthly}]" \
      --profile "$PROFILE" \
      > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo "✓ Tagged"
        ((SUCCESS++))
    else
        echo "✗ FAILED"
        ((FAILED++))
    fi
done

echo ""
echo "==========================================="
echo "Summary"
echo "==========================================="
echo "Successfully tagged: $SUCCESS"
echo "Failed: $FAILED"
echo ""
echo "Monthly backups will be retained for 13 months (395 days)"
echo "  - Day 1+: Moved to Glacier"
echo "  - Day 395: Deleted"
echo ""
echo "All other backups: 90-day retention (weekly)"
echo ""

if [ $FAILED -gt 0 ]; then
    exit 1
fi

exit 0
