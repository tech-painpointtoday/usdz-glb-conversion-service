#!/bin/bash

# Build script for EC2
# Run this on your EC2 instance after uploading the files

set -e

echo "🚀 Building Lambda Docker Image on EC2"
echo "======================================"
echo ""

# Set variables
export AWS_REGION="ap-southeast-1"
export ECR_REPO_NAME="usdz-glb-lambda"
export IMAGE_TAG="latest"

# Get AWS Account ID
echo "📋 Getting AWS Account ID..."
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Error: Could not get AWS Account ID"
    echo "   Make sure AWS CLI is configured: aws configure"
    exit 1
fi

echo "✅ AWS Account ID: $AWS_ACCOUNT_ID"
echo ""

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo "✅ Logged in to ECR"
echo ""

# Build Docker image
echo "🏗️  Building Docker image..."
echo "   This may take 5-10 minutes..."
docker build -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Docker image built"
echo ""

# Tag image
echo "🏷️  Tagging image..."
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

echo "✅ Image tagged"
echo ""

# Push to ECR
echo "⬆️  Pushing image to ECR..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

if [ $? -ne 0 ]; then
    echo "❌ Push failed"
    exit 1
fi

echo ""
echo "======================================"
echo "✨ SUCCESS! Image pushed to ECR"
echo "======================================"
echo ""
echo "📋 Image URI (copy this for Lambda):"
echo ""
echo "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}"
echo ""
