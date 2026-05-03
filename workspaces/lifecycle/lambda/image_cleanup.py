"""
WorkSpaces Image Cleanup
Deletes backup images after 90-day retention period.
"""
import os
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
DRY_RUN = os.environ.get('DRY_RUN_MODE', 'true').lower() == 'true'
TRACKING_TABLE = os.environ['TRACKING_TABLE']

# AWS clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TRACKING_TABLE)
sts = boto3.client('sts')
ssm = boto3.client('ssm')

def lambda_handler(event, context):
    """Main handler - runs daily"""
    logger.info(f"Starting image cleanup (DRY_RUN={DRY_RUN})")

    # Get accounts to scan
    accounts = get_accounts_to_scan()

    stats = {
        'accounts_scanned': 0,
        'images_checked': 0,
        'images_deleted': 0,
        'errors': 0
    }

    for account_id in accounts:
        try:
            logger.info(f"Checking images in account: {account_id}")
            account_stats = process_account(account_id)
            stats['accounts_scanned'] += 1
            stats['images_checked'] += account_stats.get('images_checked', 0)
            stats['images_deleted'] += account_stats.get('images_deleted', 0)
        except Exception as e:
            logger.error(f"Error processing account {account_id}: {str(e)}")
            stats['errors'] += 1

    logger.info(f"Cleanup complete: {stats}")
    return {'statusCode': 200, 'body': stats}

def get_accounts_to_scan():
    """Get list of AWS account IDs from SSM Parameter"""
    try:
        response = ssm.get_parameter(Name='/workspaces/lifecycle/accounts-to-scan')
        accounts = response['Parameter']['Value'].split(',')
        return [acc.strip() for acc in accounts]
    except Exception as e:
        logger.error(f"Failed to get accounts from SSM: {str(e)}")
        return [sts.get_caller_identity()['Account']]

def process_account(account_id: str):
    """Process all WorkSpace images in an account"""
    stats = {'images_checked': 0, 'images_deleted': 0}

    # Assume cross-account role
    try:
        creds = assume_role(account_id)
        ws_client = boto3.client('workspaces', **creds)
    except Exception as e:
        logger.error(f"Failed to assume role in {account_id}: {str(e)}")
        return stats

    # Get all images with AutoCleanup tag
    try:
        images = ws_client.describe_workspace_images()['Images']

        for image in images:
            # Check if managed by COSE automation
            tags = {tag['Key']: tag['Value'] for tag in image.get('Tags', [])}

            if tags.get('AutoCleanup') != 'true':
                continue

            stats['images_checked'] += 1

            # Check expiration date
            delete_after = tags.get('DeleteAfter')
            if not delete_after:
                logger.warning(f"Image {image['ImageId']} has AutoCleanup but no DeleteAfter tag")
                continue

            expiration_date = datetime.strptime(delete_after, '%Y-%m-%d')

            if datetime.now() >= expiration_date:
                logger.info(f"Deleting expired image: {image['ImageId']} (expired {delete_after})")
                delete_image(ws_client, image['ImageId'], tags.get('OriginalWorkspace'))
                stats['images_deleted'] += 1

    except Exception as e:
        logger.error(f"Failed to process images in {account_id}: {str(e)}")

    return stats

def assume_role(account_id: str):
    """Assume cross-account role"""
    role_arn = f"arn:aws:iam::{account_id}:role/WorkSpacesLifecycleRole"
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName='WorkSpacesImageCleanup'
    )
    creds = response['Credentials']
    return {
        'aws_access_key_id': creds['AccessKeyId'],
        'aws_secret_access_key': creds['SecretAccessKey'],
        'aws_session_token': creds['SessionToken']
    }

def delete_image(ws_client, image_id: str, original_workspace: str):
    """Delete WorkSpace image and update tracking"""
    if DRY_RUN:
        logger.info(f"[DRY_RUN] Would delete image {image_id}")
        return

    try:
        # Delete image
        ws_client.delete_workspace_image(ImageId=image_id)
        logger.info(f"Deleted image {image_id}")

        # Update DynamoDB tracking
        if original_workspace:
            table.update_item(
                Key={'WorkspaceId': original_workspace},
                UpdateExpression='SET ImageDeletedDate = :date',
                ExpressionAttributeValues={
                    ':date': datetime.now().isoformat()
                }
            )

    except Exception as e:
        logger.error(f"Failed to delete image {image_id}: {str(e)}")
        raise
