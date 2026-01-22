# EC2 Build Setup - Step by Step Guide

## Step 1: Launch EC2 Instance

1. Go to AWS Console → **EC2** → **Launch Instance**

2. Configure:
   - **Name**: `lambda-docker-build`
   - **AMI**: Amazon Linux 2023 (default, free tier eligible)
   - **Instance type**: t3.medium (faster build) or t2.micro (free tier, slower)
   - **Key pair**: 
     - If you have one: Select existing
     - If not: Click "Create new key pair" → Name: `lambda-build-key` → Download .pem file
   - **Network settings**: 
     - Allow SSH traffic from "My IP"
   - **Storage**: 30 GiB (default is fine)

3. Click **Launch instance**

4. Wait 1-2 minutes for instance to start

## Step 2: Connect to EC2

### Option A: EC2 Instance Connect (Easiest - No SSH key needed)

1. In EC2 Console, select your instance
2. Click **Connect** button (top right)
3. Click **Connect** on EC2 Instance Connect tab
4. A terminal will open in your browser ✅

### Option B: SSH from Terminal (if you prefer)

```bash
chmod 400 ~/Downloads/lambda-build-key.pem
ssh -i ~/Downloads/lambda-build-key.pem ec2-user@YOUR-INSTANCE-PUBLIC-IP
```

## Step 3: Setup Docker on EC2

Once connected, run these commands:

```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (so you don't need sudo)
sudo usermod -a -G docker ec2-user

# Apply group changes
newgrp docker

# Test Docker
docker --version
```

Expected output: `Docker version 24.x.x`

## Step 4: Configure AWS CLI

```bash
# AWS CLI is pre-installed on Amazon Linux
aws --version

# Configure with your credentials
aws configure
```

Enter:
- AWS Access Key ID: `[Your access key]`
- AWS Secret Access Key: `[Your secret key]`
- Default region name: `ap-southeast-1`
- Default output format: `json`

Test it:
```bash
aws sts get-caller-identity
```

Should show your account ID: 376619796260

## Step 5: Create Files on EC2

```bash
# Create working directory
mkdir ~/lambda-build
cd ~/lambda-build

# Create lambda_function.py (copy/paste this entire block)
cat > lambda_function.py << 'EOF'
import json
import boto3
import subprocess
import os
import tempfile
import traceback

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    print(f"Event received: {json.dumps(event)}")
    
    try:
        # Get bucket and key
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key'].strip()
        
        print(f"Bucket: {bucket}")
        print(f"Key: {key}")
        
        if not key.lower().endswith('.usdz'):
            print(f"File is not USDZ, skipping: {key}")
            return {'statusCode': 200, 'body': json.dumps('Not a USDZ file')}
        
        print(f"Processing USDZ file: {bucket}/{key}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            usdz_path = os.path.join(temp_dir, 'input.usdz')
            glb_path = os.path.join(temp_dir, 'output.glb')
            
            print(f"Downloading from S3: s3://{bucket}/{key}")
            
            try:
                s3_client.download_file(bucket, key, usdz_path)
                file_size = os.path.getsize(usdz_path)
                print(f"✅ Downloaded USDZ file ({file_size} bytes)")
            except Exception as e:
                print(f"❌ Failed to download file: {str(e)}")
                raise
            
            print("Checking gltf-transform availability...")
            check_result = subprocess.run(
                ['which', 'gltf-transform'],
                capture_output=True,
                text=True
            )
            print(f"gltf-transform location: {check_result.stdout.strip()}")
            
            if check_result.returncode != 0:
                raise Exception("gltf-transform not found in container")
            
            print(f"Converting USDZ to GLB...")
            result = subprocess.run(
                ['gltf-transform', 'copy', usdz_path, glb_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            print(f"Conversion stdout: {result.stdout}")
            print(f"Conversion stderr: {result.stderr}")
            print(f"Conversion return code: {result.returncode}")
            
            if result.returncode != 0:
                error_msg = f'Conversion failed: {result.stderr}'
                print(f"❌ {error_msg}")
                return {'statusCode': 500, 'body': json.dumps(error_msg)}
            
            if not os.path.exists(glb_path):
                raise Exception(f"GLB file was not created at {glb_path}")
            
            glb_size = os.path.getsize(glb_path)
            print(f"✅ GLB file created ({glb_size} bytes)")
            
            glb_key = key.rsplit('.', 1)[0] + '.glb'
            print(f"Uploading GLB to S3: s3://{bucket}/{glb_key}")
            
            s3_client.upload_file(
                glb_path, 
                bucket, 
                glb_key,
                ExtraArgs={'ContentType': 'model/gltf-binary'}
            )
            
            print(f"✅ Successfully uploaded GLB: {glb_key}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Conversion successful',
                    'input': key,
                    'output': glb_key,
                    'input_size': file_size,
                    'output_size': glb_size
                })
            }
            
    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ {error_msg}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
EOF

# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM public.ecr.aws/lambda/python:3.11

# Install Node.js from Amazon Linux Extras
RUN yum install -y amazon-linux-extras && \
    amazon-linux-extras enable nodejs18 && \
    yum clean metadata && \
    yum install -y nodejs npm && \
    yum clean all

# Verify Node.js installation
RUN node --version && npm --version

# Install gltf-transform CLI globally
RUN npm install -g @gltf-transform/cli

# Verify gltf-transform installation
RUN which gltf-transform && gltf-transform --version

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Install Python dependencies
RUN pip install boto3 --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]
EOF

echo "✅ Files created successfully"
ls -la
```

## Step 6: Build and Push to ECR

```bash
# Set variables
export AWS_REGION="ap-southeast-1"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO_NAME="usdz-glb-lambda"
export IMAGE_TAG="latest"

echo "Account ID: $AWS_ACCOUNT_ID"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build Docker image (this takes 5-8 minutes)
docker build -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

# Tag image
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Push to ECR (this takes 2-3 minutes)
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Display the Image URI
echo ""
echo "✅✅✅ SUCCESS! ✅✅✅"
echo ""
echo "Copy this Image URI for Lambda:"
echo "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}"
echo ""
```

## Step 7: Copy the Image URI

Copy the URI from the output. It will look like:
```
376619796260.dkr.ecr.ap-southeast-1.amazonaws.com/usdz-glb-lambda:latest
```

## Step 8: Clean Up

After successful push:

```bash
# Exit EC2
exit

# Go to EC2 Console → Select instance → Instance state → Terminate instance
```

Cost: ~$0.02 USD for ~15 minutes of t3.medium usage.

---

## Troubleshooting

**If AWS CLI config fails:**
- Make sure you have AWS Access Key and Secret Key ready
- Get them from IAM Console → Users → Your user → Security credentials

**If Docker build fails:**
- Make sure you ran `newgrp docker` after adding user to group
- Try `sudo docker build ...` if needed

**If ECR push fails:**
- Check your IAM user has ECR permissions
- Verify repository exists: `aws ecr describe-repositories --region ap-southeast-1`
