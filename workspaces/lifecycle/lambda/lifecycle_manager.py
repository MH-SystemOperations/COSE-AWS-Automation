"""
WorkSpaces Lifecycle Manager
Detects unused WorkSpaces, sends warnings, creates backups, and terminates.
"""
import os
import boto3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
DRY_RUN = os.environ.get('DRY_RUN_MODE', 'true').lower() == 'true'
TEST_WORKSPACE_ID = os.environ.get('TEST_WORKSPACE_ID', '').strip()  # For testing - only process this WorkSpace
TRACKING_TABLE = os.environ['TRACKING_TABLE']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
UNUSED_THRESHOLD_DAYS = int(os.environ.get('UNUSED_THRESHOLD_DAYS', '90'))
WARNING_PERIOD_DAYS = int(os.environ.get('WARNING_PERIOD_DAYS', '14'))

# AWS clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TRACKING_TABLE)
sns = boto3.client('sns')
ssm = boto3.client('ssm')
sts = boto3.client('sts')

def lambda_handler(event, context):
    """Main handler - runs weekly"""
    test_mode = " TEST_MODE" if TEST_WORKSPACE_ID else ""
    logger.info(f"Starting WorkSpaces lifecycle scan (DRY_RUN={DRY_RUN}{test_mode})")
    if TEST_WORKSPACE_ID:
        logger.info(f"TEST MODE: Only processing WorkSpace {TEST_WORKSPACE_ID}")

    # Get configuration
    accounts = get_accounts_to_scan()
    excluded_patterns = get_excluded_patterns()

    stats = {
        'accounts_scanned': 0,
        'workspaces_found': 0,
        'unused_detected': 0,
        'warnings_sent': 0,
        'deletions_completed': 0,
        'errors': 0
    }

    # Process each account
    for account_id in accounts:
        try:
            logger.info(f"Scanning account: {account_id}")
            account_stats = process_account(account_id, excluded_patterns)
            stats['accounts_scanned'] += 1
            for key in ['workspaces_found', 'unused_detected', 'warnings_sent', 'deletions_completed']:
                stats[key] += account_stats.get(key, 0)
        except Exception as e:
            logger.error(f"Error processing account {account_id}: {str(e)}")
            stats['errors'] += 1

    logger.info(f"Scan complete: {stats}")
    return {'statusCode': 200, 'body': stats}

def get_accounts_to_scan() -> List[str]:
    """Get list of AWS account IDs to scan from SSM Parameter"""
    try:
        response = ssm.get_parameter(Name='/workspaces/lifecycle/accounts-to-scan')
        accounts = response['Parameter']['Value'].split(',')
        return [acc.strip() for acc in accounts]
    except Exception as e:
        logger.error(f"Failed to get accounts from SSM: {str(e)}")
        return [sts.get_caller_identity()['Account']]

def get_excluded_patterns() -> List[str]:
    """Get regex patterns for excluded usernames from SSM"""
    try:
        response = ssm.get_parameter(Name='/workspaces/lifecycle/excluded-users')
        patterns = response['Parameter']['Value'].split(',')
        return [p.strip() for p in patterns]
    except Exception as e:
        logger.warning(f"Failed to get exclusions from SSM: {str(e)}")
        return ['CAR-.*', 'cmh-.*', 'LAI-.*']

def process_account(account_id: str, excluded_patterns: List[str]) -> Dict:
    """Process all WorkSpaces in an account"""
    stats = {'workspaces_found': 0, 'unused_detected': 0, 'warnings_sent': 0, 'deletions_completed': 0}

    # Assume cross-account role
    try:
        creds = assume_role(account_id)
        ws_client = boto3.client('workspaces', **creds)
        cw_client = boto3.client('cloudwatch', **creds)
    except Exception as e:
        logger.error(f"Failed to assume role in {account_id}: {str(e)}")
        return stats

    # Get WorkSpaces (single or all depending on test mode)
    if TEST_WORKSPACE_ID:
        # Test mode: Query specific WorkSpace directly
        try:
            response = ws_client.describe_workspaces(WorkspaceIds=[TEST_WORKSPACE_ID])
            workspaces = response.get('Workspaces', [])
            if not workspaces:
                logger.warning(f"TEST_WORKSPACE_ID {TEST_WORKSPACE_ID} not found in account {account_id}")
                return stats
        except Exception as e:
            logger.warning(f"TEST_WORKSPACE_ID {TEST_WORKSPACE_ID} not found in account {account_id}: {str(e)}")
            return stats
    else:
        # Production mode: Get all WorkSpaces
        workspaces = get_all_workspaces(ws_client)

    stats['workspaces_found'] = len(workspaces)

    for ws in workspaces:
        # Skip excluded users (unless in test mode)
        if not TEST_WORKSPACE_ID and is_excluded(ws['UserName'], excluded_patterns):
            logger.debug(f"Skipping excluded user: {ws['UserName']}")
            continue

        # Check if already tracked
        tracking = get_tracking_record(ws['WorkspaceId'])

        if tracking and tracking['Status'] == 'KeepAlive':
            logger.info(f"Skipping KeepAlive WorkSpace: {ws['WorkspaceId']}")
            continue

        if tracking and tracking['Status'] == 'WarningPending':
            # Check if deletion date reached
            deletion_date = datetime.fromisoformat(tracking['DeletionDate'])
            if datetime.now() >= deletion_date:
                # Re-verify usage before deletion
                usage = check_usage(cw_client, ws['WorkspaceId'], WARNING_PERIOD_DAYS)
                if usage > 0:
                    logger.info(f"Aborting deletion - usage detected: {ws['WorkspaceId']}")
                    update_tracking(ws['WorkspaceId'], 'UserResponded')
                else:
                    # Proceed with deletion
                    delete_workspace(ws_client, ws, account_id, cw_client)
                    stats['deletions_completed'] += 1
        else:
            # New WorkSpace - check usage
            usage = check_usage(cw_client, ws['WorkspaceId'], UNUSED_THRESHOLD_DAYS)
            if usage == 0:
                logger.info(f"Unused WorkSpace detected: {ws['WorkspaceId']} ({ws['UserName']})")
                stats['unused_detected'] += 1
                send_warning(ws, account_id)
                stats['warnings_sent'] += 1

    return stats

def assume_role(account_id: str) -> Dict:
    """Assume cross-account role"""
    role_arn = f"arn:aws:iam::{account_id}:role/WorkSpacesLifecycleRole"
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName='WorkSpacesLifecycleManager',
        ExternalId='WorkSpacesLifecycle-COSE'
    )
    creds = response['Credentials']
    return {
        'aws_access_key_id': creds['AccessKeyId'],
        'aws_secret_access_key': creds['SecretAccessKey'],
        'aws_session_token': creds['SessionToken']
    }

def get_all_workspaces(client) -> List[Dict]:
    """Get all WorkSpaces in account"""
    workspaces = []
    paginator = client.get_paginator('describe_workspaces')
    for page in paginator.paginate():
        workspaces.extend(page['Workspaces'])
    return workspaces

def is_excluded(username: str, patterns: List[str]) -> bool:
    """Check if username matches exclusion patterns"""
    for pattern in patterns:
        if re.match(pattern, username):
            return True
    return False

def check_usage(cw_client, workspace_id: str, days: int) -> float:
    """Check WorkSpace usage via CloudWatch UserConnected metric"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

    try:
        response = cw_client.get_metric_statistics(
            Namespace='AWS/WorkSpaces',
            MetricName='UserConnected',
            Dimensions=[{'Name': 'WorkspaceId', 'Value': workspace_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400 * days,
            Statistics=['Sum']
        )

        if response['Datapoints']:
            return response['Datapoints'][0]['Sum']
        return 0.0
    except Exception as e:
        logger.error(f"Failed to check usage for {workspace_id}: {str(e)}")
        return None

def get_tracking_record(workspace_id: str) -> Optional[Dict]:
    """Get tracking record from DynamoDB"""
    try:
        response = table.get_item(Key={'WorkspaceId': workspace_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Failed to get tracking record for {workspace_id}: {str(e)}")
        return None

def update_tracking(workspace_id: str, status: str):
    """Update tracking record status"""
    if DRY_RUN:
        logger.info(f"[DRY_RUN] Would update {workspace_id} to {status}")
        return

    try:
        table.update_item(
            Key={'WorkspaceId': workspace_id},
            UpdateExpression='SET #status = :status, UpdatedDate = :date',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': status,
                ':date': datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Failed to update tracking for {workspace_id}: {str(e)}")

def send_warning(ws: Dict, account_id: str):
    """Send warning email to user"""
    deletion_date = datetime.now() + timedelta(days=WARNING_PERIOD_DAYS)

    message = f"""
WorkSpace Scheduled for Deletion - Action Required

Username: {ws['UserName']}
WorkSpace ID: {ws['WorkspaceId']}
Account: {account_id}

Our records show this WorkSpace has not been accessed in {UNUSED_THRESHOLD_DAYS}+ days.

To help optimize AWS costs, we're planning to delete unused WorkSpaces.

ACTION REQUIRED:
If you still need this WorkSpace, take action within {WARNING_PERIOD_DAYS} days.

Scheduled deletion date: {deletion_date.strftime('%B %d, %Y')}

TO KEEP THIS WORKSPACE (choose one):
1. Log in to your WorkSpace (we'll detect the activity and cancel deletion)
2. Email servicedesk@marathon-health.org with WorkSpace ID: {ws['WorkspaceId']}

IMPORTANT:
- A backup image will be created before deletion
- If deleted, we can restore your WorkSpace from the backup within 90 days
- Please back up any important files to OneDrive or network storage
- After 90 days, the backup will be permanently deleted

Questions? Contact servicedesk@marathon-health.org

---
This is an automated message from COSE AWS Automation.
    """

    if DRY_RUN:
        logger.info(f"[DRY_RUN] Would send warning email for {ws['WorkspaceId']}")
        logger.debug(f"Message: {message}")
    else:
        try:
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject='WorkSpace Scheduled for Deletion - Action Required',
                Message=message
            )
            # Record warning sent
            table.put_item(Item={
                'WorkspaceId': ws['WorkspaceId'],
                'AccountId': account_id,
                'UserName': ws['UserName'],
                'WarningSentDate': datetime.now().isoformat(),
                'DeletionDate': deletion_date.isoformat(),
                'Status': 'WarningPending',
                'WorkspaceDetails': {
                    'State': ws['State'],
                    'BundleId': ws['BundleId'],
                    'DirectoryId': ws['DirectoryId'],
                    'SubnetId': ws.get('SubnetId', '')
                }
            })
            logger.info(f"Warning sent for {ws['WorkspaceId']}")
        except Exception as e:
            logger.error(f"Failed to send warning for {ws['WorkspaceId']}: {str(e)}")

def delete_workspace(ws_client, ws: Dict, account_id: str, cw_client):
    """Create backup image and delete WorkSpace"""
    workspace_id = ws['WorkspaceId']

    if DRY_RUN:
        logger.info(f"[DRY_RUN] Would delete {workspace_id} after creating backup image")
        return

    try:
        # Start WorkSpace if stopped (required for image creation)
        if ws['State'] == 'STOPPED':
            logger.info(f"Starting {workspace_id} for image creation")
            ws_client.start_workspaces(StartWorkspaceRequests=[{'WorkspaceId': workspace_id}])
            logger.info(f"WorkSpace {workspace_id} starting - will create image in next run")
            return

        # Create image
        image_name = f"backup-{ws['UserName']}-{datetime.now().strftime('%Y%m%d')}"
        image_response = ws_client.create_workspace_image(
            Name=image_name,
            Description=f"Auto-backup before deletion - expires {(datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')}",
            WorkspaceId=workspace_id
        )

        image_id = image_response['ImageId']
        logger.info(f"Created backup image {image_id} for {workspace_id}")

        # Tag image
        ws_client.create_tags(
            ResourceId=image_id,
            Tags=[
                {'Key': 'DeleteAfter', 'Value': (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')},
                {'Key': 'OriginalWorkspace', 'Value': workspace_id},
                {'Key': 'AutoCleanup', 'Value': 'true'},
                {'Key': 'ManagedBy', 'Value': 'COSE-AWS-Automation'}
            ]
        )

        # Delete WorkSpace
        ws_client.terminate_workspaces(
            TerminateWorkspaceRequests=[{'WorkspaceId': workspace_id}]
        )

        # Update tracking
        table.update_item(
            Key={'WorkspaceId': workspace_id},
            UpdateExpression='SET #status = :status, DeletedDate = :date, ImageId = :image',
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues={
                ':status': 'Deleted',
                ':date': datetime.now().isoformat(),
                ':image': image_id
            }
        )

        logger.info(f"Deleted WorkSpace {workspace_id}, backup: {image_id}")

    except Exception as e:
        logger.error(f"Failed to delete {workspace_id}: {str(e)}")
        raise
