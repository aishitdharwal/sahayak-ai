#!/bin/bash
# Sahayak AI — EC2 CloudFormation Deploy Script
# Usage: bash deploy/cloudformation/deploy-ec2.sh [REGION] [STACK_NAME]
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - EC2 key pair created in the target region
#   - parameters/ec2-params.json filled in

set -e

REGION="${1:-ap-south-1}"
STACK_NAME="${2:-sahayak-ec2}"
TEMPLATE="deploy/cloudformation/ec2.yml"
PARAMS="deploy/cloudformation/parameters/ec2-params.json"

echo "=== Sahayak AI — EC2 Deploy ==="
echo "Region:     $REGION"
echo "Stack:      $STACK_NAME"
echo ""

# Validate the template before deploying
echo "Validating CloudFormation template..."
aws cloudformation validate-template \
  --template-body file://$TEMPLATE \
  --region $REGION > /dev/null
echo "Template valid."

# Check if stack already exists
if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION &>/dev/null; then
  echo "Stack exists — running UPDATE..."
  OPERATION="update-stack"
else
  echo "Stack not found — running CREATE..."
  OPERATION="create-stack"
fi

aws cloudformation $OPERATION \
  --stack-name $STACK_NAME \
  --template-body file://$TEMPLATE \
  --parameters file://$PARAMS \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION

echo ""
echo "Waiting for stack to complete (this takes ~5 minutes while EC2 bootstraps)..."
aws cloudformation wait stack-${OPERATION//-stack/}-complete \
  --stack-name $STACK_NAME \
  --region $REGION

echo ""
echo "=== Deploy complete ==="

# Print outputs
echo ""
echo "Stack outputs:"
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query "Stacks[0].Outputs[*].[OutputKey, OutputValue]" \
  --output table

echo ""
echo "NOTE: EC2 UserData (first-boot setup) may still be running."
echo "Watch progress: SSH in and run:"
echo "  sudo tail -f /var/log/sahayak-setup.log"
