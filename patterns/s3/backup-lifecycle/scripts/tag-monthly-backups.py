#!/usr/bin/env python3
"""
Automatically tag the latest backup of each month for 13-month retention
Run monthly to maintain rolling 13-month monthly backup retention
"""

import boto3
import sys
from datetime import datetime, timedelta
from collections import defaultdict

def main():
    # Configuration
    bucket = sys.argv[1] if len(sys.argv) > 1 else "mh-edw-backup"
    profile = sys.argv[2] if len(sys.argv) > 2 else "mh-ops"
    months_to_keep = int(sys.argv[3]) if len(sys.argv) > 3 else 13
    prefix_filter = sys.argv[4] if len(sys.argv) > 4 else "Consolidated_"

    print("=" * 60)
    print("Monthly Backup Tagging Script")
    print("=" * 60)
    print(f"Bucket: {bucket}")
    print(f"Profile: {profile}")
    print(f"Prefix filter: {prefix_filter}")
    print(f"Months to keep: {months_to_keep}")
    print()

    # Initialize S3 client
    session = boto3.Session(profile_name=profile)
    s3 = session.client('s3')

    # Step 1: List all backup files
    print("Step 1: Finding all backup files...")
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket)

    files = []
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                # Filter: must contain prefix and end with .bak
                if prefix_filter in key and key.endswith('.bak'):
                    # Exclude Dev, QA, Test backups for production monthly retention
                    if not any(x in key for x in ['_Dev', '_QA', '_Test']):
                        files.append({
                            'key': key,
                            'last_modified': obj['LastModified']
                        })

    print(f"Found {len(files)} backup files matching criteria")
    print()

    if not files:
        print("ERROR: No files found")
        return 1

    # Step 2: Group by month and find latest in each month
    print("Step 2: Identifying latest backup per month...")
    monthly_backups = defaultdict(lambda: None)

    for file in files:
        year_month = file['last_modified'].strftime('%Y-%m')

        # Keep the latest file for each month
        if monthly_backups[year_month] is None or \
           file['last_modified'] > monthly_backups[year_month]['last_modified']:
            monthly_backups[year_month] = file

    # Filter to only last N months
    from datetime import timezone
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=months_to_keep * 30)
    filtered_backups = {
        month: file for month, file in monthly_backups.items()
        if file['last_modified'] >= cutoff_date
    }

    print(f"Found {len(filtered_backups)} monthly backups to tag:")
    for month in sorted(filtered_backups.keys(), reverse=True):
        print(f"  {month}: {filtered_backups[month]['key']}")
    print()

    # Step 3: Tag each monthly backup
    print("Step 3: Tagging monthly backups...")
    success = 0
    failed = 0

    for month in sorted(filtered_backups.keys(), reverse=True):
        file = filtered_backups[month]
        key = file['key']

        print(f"Tagging: {key} ... ", end='', flush=True)

        try:
            # Check existing tags
            try:
                existing = s3.get_object_tagging(Bucket=bucket, Key=key)
                tags = existing.get('TagSet', [])
                if any(t['Key'] == 'Retention' and t['Value'] == 'Monthly' for t in tags):
                    print("[OK] Already tagged (skipped)")
                    success += 1
                    continue
            except:
                pass

            # Apply Monthly retention tag
            s3.put_object_tagging(
                Bucket=bucket,
                Key=key,
                Tagging={
                    'TagSet': [
                        {'Key': 'Retention', 'Value': 'Monthly'}
                    ]
                }
            )
            print("[OK] Tagged")
            success += 1

        except Exception as e:
            print(f"[FAIL] FAILED: {e}")
            failed += 1

    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Successfully tagged: {success}")
    print(f"Failed: {failed}")
    print()
    print("Monthly backups will be retained for 13 months (395 days)")
    print("  - Day 1+: Moved to Glacier")
    print("  - Day 395: Deleted")
    print()
    print("All other backups: 90-day retention (weekly)")
    print()

    return 1 if failed > 0 else 0

if __name__ == '__main__':
    sys.exit(main())
