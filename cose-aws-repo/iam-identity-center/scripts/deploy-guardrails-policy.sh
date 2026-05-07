#!/bin/bash
# Deploy MH-Engineer-Guardrails customer-managed policy to all accounts that need write access
#
# Prerequisites:
# - AWS CLI configured with mh-ops profile (Administrator access to management account)
# - OrganizationAccountAccessRole exists in each member account
#
# Usage: ./deploy-guardrails-policy.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY_FILE="$SCRIPT_DIR/../policies/mh-engineer-guardrails-v2.json"

ACCOUNTS=(
  "123185598779"  # Platform Sandbox
  "201799325713"  # Platform Data Dev
  "808468589041"  # Platform Data QA
  "686255955782"  # Platform Digital Tools Dev
  "593793032905"  # Platform Digital Tools QA
  "971318514578"  # Platform Data Prod
  "266565038828"  # MH System Operations (management account - use direct profile)
  "209479269442"  # Platform Digital Tools Staging
  "476114142697"  # Platform Digital Tools Prod
  "339712701706"  # Pharmacy Prod
)

echo "🚀 Deploying MH-Engineer-Guardrails policy to 10 accounts..."
echo ""

SUCCESS_COUNT=0
SKIP_COUNT=0
FAIL_COUNT=0

for account in "${ACCOUNTS[@]}"; do
  echo "📋 Processing account $account..."

  # Management account uses direct profile, others use assume role
  if [ "$account" == "266565038828" ]; then
    CREDENTIALS=""
    PROFILE_ARG="--profile mh-ops"
  else
    # Assume OrganizationAccountAccessRole in member account
    ROLE_ARN="arn:aws:iam::$account:role/OrganizationAccountAccessRole"

    echo "   Assuming role: $ROLE_ARN"
    CREDENTIALS=$(aws sts assume-role \
      --role-arn "$ROLE_ARN" \
      --role-session-name "deploy-guardrails-$(date +%s)" \
      --profile mh-ops \
      --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' \
      --output text 2>/dev/null)

    if [ -z "$CREDENTIALS" ]; then
      echo "  ❌ Failed to assume role in $account"
      ((FAIL_COUNT++))
      echo ""
      continue
    fi

    # Extract credentials
    ACCESS_KEY=$(echo "$CREDENTIALS" | awk '{print $1}')
    SECRET_KEY=$(echo "$CREDENTIALS" | awk '{print $2}')
    SESSION_TOKEN=$(echo "$CREDENTIALS" | awk '{print $3}')

    # Set environment variables for this iteration
    export AWS_ACCESS_KEY_ID="$ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="$SECRET_KEY"
    export AWS_SESSION_TOKEN="$SESSION_TOKEN"
    PROFILE_ARG=""
  fi

  # Try to create the policy
  OUTPUT=$(aws iam create-policy \
    --policy-name MH-Engineer-Guardrails \
    --policy-document file://$POLICY_FILE \
    --description "Guardrails for MH-Engineer and MH-Lead permission sets - blocks privilege escalation, expensive resources, and audit tampering" \
    $PROFILE_ARG \
    --region us-east-1 2>&1) || CREATE_FAILED=$?

  if [ -z "$CREATE_FAILED" ]; then
    echo "  ✅ Created policy in $account"
    ((SUCCESS_COUNT++))
  else
    # Check if it already exists
    if echo "$OUTPUT" | grep -q "EntityAlreadyExists"; then
      echo "  ⚠️  Policy already exists in $account"
      ((SKIP_COUNT++))
    else
      echo "  ❌ Failed to create policy in $account"
      echo "     Error: $OUTPUT"
      ((FAIL_COUNT++))
    fi
  fi

  # Clear credentials for next iteration
  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN CREATE_FAILED
  echo ""
done

echo "===================="
echo "📊 Deployment Summary"
echo "===================="
echo "✅ Created: $SUCCESS_COUNT"
echo "⚠️  Skipped (already exists): $SKIP_COUNT"
echo "❌ Failed: $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -gt 0 ]; then
  echo "⚠️  Some deployments failed. Review errors above."
  exit 1
else
  echo "🎉 All deployments completed successfully!"
  exit 0
fi
