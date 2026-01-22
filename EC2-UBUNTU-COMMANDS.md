# EC2 Build Setup - Ubuntu Commands

You're on Ubuntu, so use these commands instead:

## Step 1: Setup Docker on Ubuntu

```bash
# Update system
sudo apt update -y

# Install Docker
sudo apt install -y docker.io

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker ubuntu

# Apply group changes
newgrp docker

# Test Docker
docker --version
```

## Step 2: Install AWS CLI

```bash
# Install AWS CLI
sudo apt install -y awscli

# Or install latest version:
# curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
# sudo apt install -y unzip
# unzip awscliv2.zip
# sudo ./aws/install

# Configure AWS
aws configure
```

Enter:
- AWS Access Key ID
- AWS Secret Access Key  
- Region: `ap-southeast-1`
- Output: `json`

## Step 3: Create Files

```bash
# Create directory
mkdir ~/lambda-build
cd ~/lambda-build

# Create lambda_function.py
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

CMD [ "lambda_function.lambda_handler" ]
EOF

echo "✅ Files created"
ls -la
```

## Step 4: Build and Push

```bash
# Set variables
export AWS_REGION="ap-southeast-1"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO_NAME="usdz-glb-lambda"
export IMAGE_TAG="latest"

echo "Building for account: $AWS_ACCOUNT_ID"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build (takes 5-8 minutes)
docker build -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

# Tag
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Push (takes 2-3 minutes)
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Show result
echo ""
echo "✅✅✅ SUCCESS ✅✅✅"
echo ""
echo "Image URI:"
echo "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}"
echo ""
```

## Step 5: Copy Image URI and Exit

```bash
# Exit EC2
exit
```

Then terminate the EC2 instance in AWS Console.
