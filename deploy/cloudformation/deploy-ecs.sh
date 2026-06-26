#!/bin/bash
# Sahayak AI — ECS CloudFormation Deploy Script
# Usage: bash deploy/cloudformation/deploy-ecs.sh [REGION] [STACK_NAME]
#
# What this script does:
#   Phase 1 — Infrastructure: deploys the CloudFormation stack (VPC, RDS, Redis, ECS, etc.)
#   Phase 2 — Image: builds the Docker image, pushes to ECR
#   Phase 3 — Secrets: writes Postgres + Redis URLs into Secrets Manager
#   Phase 4 — Service: updates ECS service to use the new image
#   Phase 5 — Frontend: builds React app, syncs to S3, invalidates CloudFront
#   Phase 6 — Seed: runs RAG indexer against the EFS-mounted ChromaDB
#
# Prerequisites:
#   - AWS CLI configured
#   - Docker running locally
#   - parameters/ecs-params.json filled in (except ECRImageUri — auto-filled)

set -e

REGION="${1:-ap-south-1}"
STACK_NAME="${2:-sahayak-ecs}"
TEMPLATE="deploy/cloudformation/ecs.yml"
PARAMS_FILE="deploy/cloudformation/parameters/ecs-params.json"

echo "=== Sahayak AI — ECS Deploy ==="
echo "Region:     $REGION"
echo "Stack:      $STACK_NAME"
echo ""

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/sahayak-ai"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: Deploy or update the CloudFormation infrastructure stack
# ─────────────────────────────────────────────────────────────────────────────
echo "[1/6] Deploying CloudFormation infrastructure..."

aws cloudformation validate-template \
  --template-body file://$TEMPLATE \
  --region $REGION > /dev/null

if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION &>/dev/null; then
  OPERATION="update-stack"
else
  OPERATION="create-stack"
fi

# On first deploy ECRImageUri doesn't exist yet — use a placeholder
# ECS service won't start until Phase 4 updates it
PARAMS=$(cat $PARAMS_FILE | python3 -c "
import json, sys
params = json.load(sys.stdin)
for p in params:
    if p['ParameterKey'] == 'ECRImageUri':
        p['ParameterValue'] = '$ECR_URI:latest'
print(json.dumps(params))
")

aws cloudformation $OPERATION \
  --stack-name $STACK_NAME \
  --template-body file://$TEMPLATE \
  --parameters "$PARAMS" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION

echo "Waiting for infrastructure stack..."
aws cloudformation wait stack-${OPERATION//-stack/}-complete \
  --stack-name $STACK_NAME --region $REGION

# Fetch stack outputs
get_output() {
  aws cloudformation describe-stacks \
    --stack-name $STACK_NAME --region $REGION \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
    --output text
}

ALB_DNS=$(get_output ALBEndpoint)
CF_URL=$(get_output CloudFrontURL)
S3_BUCKET=$(get_output FrontendBucketName)
RDS_HOST=$(get_output RDSEndpoint)
REDIS_HOST=$(get_output RedisEndpoint)
PRIVATE_SUBNET_A=$(get_output PrivateSubnetA)
ECS_SG=$(get_output ECSSecurityGroupId)

echo "Infrastructure ready."

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: Build and push Docker image to ECR
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "[2/6] Building and pushing Docker image..."

aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
FULL_IMAGE_URI="$ECR_URI:$IMAGE_TAG"

docker build \
  -f deploy/ecs/Dockerfile \
  -t "$FULL_IMAGE_URI" \
  -t "$ECR_URI:latest" \
  .

docker push "$FULL_IMAGE_URI"
docker push "$ECR_URI:latest"

echo "Image pushed: $FULL_IMAGE_URI"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: Write connection string secrets to Secrets Manager
# These are runtime values that only exist after the infra is up
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "[3/6] Writing connection string secrets..."

DB_PASSWORD=$(cat $PARAMS_FILE | python3 -c "
import json, sys
params = json.load(sys.stdin)
for p in params:
    if p['ParameterKey'] == 'DBPassword':
        print(p['ParameterValue'])
")

POSTGRES_URL="postgresql+asyncpg://sahayak:${DB_PASSWORD}@${RDS_HOST}:5432/sahayak"
REDIS_URL="redis://${REDIS_HOST}:6379"

# Create or update postgres-url secret
if aws secretsmanager describe-secret --secret-id sahayak/postgres-url --region $REGION &>/dev/null; then
  aws secretsmanager update-secret \
    --secret-id sahayak/postgres-url \
    --secret-string "$POSTGRES_URL" \
    --region $REGION > /dev/null
else
  aws secretsmanager create-secret \
    --name sahayak/postgres-url \
    --secret-string "$POSTGRES_URL" \
    --region $REGION > /dev/null
fi

# Create or update redis-url secret
if aws secretsmanager describe-secret --secret-id sahayak/redis-url --region $REGION &>/dev/null; then
  aws secretsmanager update-secret \
    --secret-id sahayak/redis-url \
    --secret-string "$REDIS_URL" \
    --region $REGION > /dev/null
else
  aws secretsmanager create-secret \
    --name sahayak/redis-url \
    --secret-string "$REDIS_URL" \
    --region $REGION > /dev/null
fi

echo "Secrets written."

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4: Force ECS service to redeploy with the new image
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "[4/6] Triggering ECS rolling deploy..."

aws ecs update-service \
  --cluster sahayak-cluster \
  --service sahayak-backend \
  --force-new-deployment \
  --region $REGION > /dev/null

echo "Rolling deploy triggered. Tasks will be replaced one by one."
echo "Watch progress: aws ecs describe-services --cluster sahayak-cluster --services sahayak-backend --region $REGION"

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5: Build React frontend and deploy to S3 + CloudFront
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "[5/6] Building and deploying React frontend..."

cd frontend
VITE_API_BASE_URL="http://$ALB_DNS" npm run build
cd ..

aws s3 sync frontend/dist/ "s3://$S3_BUCKET/" --delete --region $REGION

CF_DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Origins.Items[0].DomainName, '$S3_BUCKET')].Id" \
  --output text)

aws cloudfront create-invalidation \
  --distribution-id $CF_DIST_ID \
  --paths "/*" > /dev/null

echo "Frontend deployed. Cache invalidation in progress (~30s)."

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 6: Run RAG indexer on a one-off ECS task (seeds ChromaDB on EFS)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "[6/6] Seeding ChromaDB on EFS via one-off ECS task..."

TASK_DEF_ARN=$(aws ecs describe-task-definition \
  --task-definition sahayak-ai \
  --query taskDefinition.taskDefinitionArn \
  --output text \
  --region $REGION)

# Run the indexer as a one-off Fargate task using the same task definition
# but overriding the command to run the indexer instead of uvicorn
aws ecs run-task \
  --cluster sahayak-cluster \
  --task-definition $TASK_DEF_ARN \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_A],securityGroups=[$ECS_SG],assignPublicIp=DISABLED}" \
  --overrides '{"containerOverrides":[{"name":"sahayak-backend","command":["python","-m","backend.rag.indexer"]}]}' \
  --region $REGION > /dev/null

echo "Seed task submitted. ChromaDB index will be written to EFS."

# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== ECS Deploy Complete ==="
echo ""
echo "  Dashboard:  $CF_URL"
echo "  API:        http://$ALB_DNS/docs"
echo "  Image:      $FULL_IMAGE_URI"
echo ""
echo "Monitor ECS service:"
echo "  aws ecs describe-services --cluster sahayak-cluster --services sahayak-backend --region $REGION"
echo ""
echo "Stream logs:"
echo "  aws logs tail /ecs/sahayak-ai --follow --region $REGION"
