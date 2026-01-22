#!/bin/bash

# USDZ to GLB Lambda - Build and Push Script
# This script builds the Docker image and pushes it to AWS ECR

set -e  # Exit on error

echo "🚀 USDZ to GLB Lambda - Build and Push Script"
echo "=============================================="
echo ""

# Configuration - UPDATE THESE VALUES
AWS_REGION="ap-southeast-1"  # Your AWS region
AWS_ACCOUNT_ID=""  # Will be auto-detected
ECR_REPO_NAME="usdz-glb-lambda"
IMAGE_TAG="latest"

# Auto-detect AWS Account ID
echo "📋 Detecting AWS Account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Error: Could not detect AWS Account ID"
    echo "   Please make sure AWS CLI is installed and configured"
    echo "   Run: aws configure"
    exit 1
fi

echo "✅ AWS Account ID: $AWS_ACCOUNT_ID"
echo "✅ AWS Region: $AWS_REGION"
echo ""

# Step 1: Create ECR repository if it doesn't exist
echo "📦 Step 1: Creating ECR repository (if it doesn't exist)..."
aws ecr describe-repositories \
    --repository-names ${ECR_REPO_NAME} \
    --region ${AWS_REGION} 2>/dev/null || \
aws ecr create-repository \
    --repository-name ${ECR_REPO_NAME} \
    --region ${AWS_REGION}

echo "✅ ECR repository ready"
echo ""

# Step 2: Login to ECR
echo "🔐 Step 2: Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to login to ECR"
    exit 1
fi

echo "✅ Logged in to ECR"
echo ""

# Step 3: Build Docker image
echo "🏗️  Step 3: Building Docker image..."
echo "   This may take 5-10 minutes..."
docker build -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

if [ $? -ne 0 ]; then
    echo "❌ Error: Docker build failed"
    exit 1
fi

echo "✅ Docker image built"
echo ""

# Step 4: Tag image for ECR
echo "🏷️  Step 4: Tagging image..."
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

echo "✅ Image tagged"
echo ""

# Step 5: Push to ECR
echo "⬆️  Step 5: Pushing image to ECR..."
echo "   This may take a few minutes..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to push image to ECR"
    exit 1
fi

echo ""
echo "✅ Image pushed to ECR"
echo ""
echo "=============================================="
echo "✨ Success! Your Docker image is now in ECR"
echo "=============================================="
echo ""
echo "📋 Image URI:"
echo "   ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}"
echo ""
echo "📝 Next Steps:"
echo "   1. Go to AWS Lambda Console"
echo "   2. Create a new Lambda function (or update existing one)"
echo "   3. Select 'Container image'"
echo "   4. Use the Image URI above"
echo ""
