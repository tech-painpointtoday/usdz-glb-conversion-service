#!/bin/bash

# USDZ to GLB Lambda - Build and Push Script (Simplified)
# Assumes ECR repository already exists
# FIXED: Builds for correct platform (x86_64/AMD64) on Apple Silicon Macs

set -e  # Exit on error

echo "🚀 USDZ to GLB Lambda - Build and Push Script"
echo "=============================================="
echo ""

# Configuration
AWS_REGION="ap-southeast-1"
ECR_REPO_NAME="usdz-glb-lambda"
IMAGE_TAG="latest"

# Auto-detect AWS Account ID
echo "📋 Detecting AWS Account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Error: Could not detect AWS Account ID"
    exit 1
fi

echo "✅ AWS Account ID: $AWS_ACCOUNT_ID"
echo "✅ AWS Region: $AWS_REGION"
echo ""

# Check if repository exists
echo "📦 Checking ECR repository..."
aws ecr describe-repositories \
    --repository-names ${ECR_REPO_NAME} \
    --region ${AWS_REGION} >/dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ Error: ECR repository '${ECR_REPO_NAME}' does not exist"
    echo "   Please create it in AWS Console first"
    exit 1
fi

echo "✅ ECR repository exists"
echo ""

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to login to ECR"
    exit 1
fi

echo "✅ Logged in to ECR"
echo ""

# Build Docker image for correct platform (AWS Lambda uses x86_64)
echo "🏗️  Building Docker image for linux/amd64 platform..."
echo "   This may take 10-15 minutes on Apple Silicon Macs..."
echo "   (Building for different architecture takes longer)"
docker buildx build --platform linux/amd64 -t ${ECR_REPO_NAME}:${IMAGE_TAG} . --load

if [ $? -ne 0 ]; then
    echo "❌ Error: Docker build failed"
    exit 1
fi

echo "✅ Docker image built"
echo ""

# Tag image for ECR
echo "🏷️  Tagging image..."
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

echo "✅ Image tagged"
echo ""

# Push to ECR
echo "⬆️  Pushing image to ECR..."
echo "   This may take a few minutes..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to push image to ECR"
    exit 1
fi

echo ""
echo "=============================================="
echo "✨ SUCCESS! Your Docker image is now in ECR"
echo "=============================================="
echo ""
echo "📋 Image URI (copy this for Lambda):"
echo ""
echo "   ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}"
echo ""
echo "📝 Next Steps:"
echo "   1. Go to AWS Lambda Console"
echo "   2. Update your Lambda function"
echo "   3. Deploy > Image > Enter the URI above"
echo ""
