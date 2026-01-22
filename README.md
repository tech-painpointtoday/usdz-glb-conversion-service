# USDZ to GLB Lambda Function

This folder contains everything needed to create an AWS Lambda function that automatically converts USDZ files to GLB format when uploaded to S3.

## Files

- `lambda_function.py` - The Lambda function code (with improved logging)
- `Dockerfile` - Docker container configuration
- `build-and-push.sh` - Automated build and deployment script

## Prerequisites

Before running the build script, make sure you have:

1. **Docker Desktop** installed and running
2. **AWS CLI** installed and configured
   - Install: `brew install awscli` (on macOS)
   - Configure: `aws configure`
3. **AWS credentials** with permissions for:
   - ECR (Elastic Container Registry)
   - Lambda
   - S3

## Step 2: Build and Push to ECR

Open Terminal and run:

```bash
cd ~/Desktop/usdz-glb-lamda
./build-and-push.sh
```

This script will:
1. ✅ Auto-detect your AWS Account ID
2. ✅ Create ECR repository
3. ✅ Login to ECR
4. ✅ Build Docker image (takes 5-10 minutes)
5. ✅ Tag and push to ECR

## What the Script Does

The build process will:
- Install Node.js 18 in the Lambda container
- Install `gltf-transform` CLI tool
- Copy your Python Lambda function
- Create a container image ready for Lambda

## After Build Completes

You'll see output like:

```
✨ Success! Your Docker image is now in ECR

📋 Image URI:
   123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/usdz-glb-lambda:latest
```

**Copy this Image URI** - you'll need it to create the Lambda function in AWS Console.

## Next Steps

Continue to AWS Console setup:
1. Create IAM role for Lambda
2. Create Lambda function using the Image URI
3. Configure S3 trigger
4. Test the function

## Troubleshooting

### "AWS CLI not found"
Install AWS CLI:
```bash
brew install awscli
aws configure
```

### "Docker not found"
- Make sure Docker Desktop is installed and running
- Download from: https://www.docker.com/products/docker-desktop

### "Permission denied"
Make script executable:
```bash
chmod +x build-and-push.sh
```

### Build takes too long
- First build takes 5-10 minutes (installing Node.js)
- Subsequent builds are faster (uses Docker cache)

## Improvements in This Version

This version includes enhanced logging:
- ✅ Shows file download progress
- ✅ Displays file sizes
- ✅ Reports conversion status
- ✅ Detailed error messages
- ✅ Checks if gltf-transform is available
- ✅ Strips trailing spaces from filenames
