# Building Lambda Docker Image on EC2

If local build fails, you can build on EC2 where network access is better.

## Step 1: Launch EC2 Instance

1. Go to EC2 Console → Launch Instance
2. Choose **Amazon Linux 2023** AMI (free tier eligible)
3. Instance type: **t3.medium** (for faster builds)
4. Key pair: Create or use existing
5. Security group: Allow SSH (port 22)
6. Storage: 30 GB
7. Launch instance

## Step 2: Connect to EC2

```bash
# From your local machine
ssh -i "your-key.pem" ec2-user@YOUR-EC2-PUBLIC-IP
```

Or use EC2 Instance Connect in AWS Console (easier).

## Step 3: Install Docker on EC2

```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -a -G docker ec2-user

# Log out and back in, or run:
newgrp docker

# Verify Docker
docker --version
```

## Step 4: Install AWS CLI (already installed on Amazon Linux)

```bash
aws --version

# Configure AWS CLI
aws configure
# Enter your Access Key ID
# Enter your Secret Access Key
# Region: ap-southeast-1
# Output format: json
```

## Step 5: Upload Files to EC2

### Option A: Using SCP (from your local machine)

```bash
cd ~/Desktop/usdz-glb-lamda
scp -i "your-key.pem" Dockerfile lambda_function.py ec2-user@YOUR-EC2-IP:~/
```

### Option B: Create files directly on EC2

```bash
# On EC2, create the files
mkdir -p ~/lambda-build
cd ~/lambda-build

# Create lambda_function.py
cat > lambda_function.py << 'EOF'
[paste the lambda_function.py content here]
EOF

# Create Dockerfile
cat > Dockerfile << 'EOF'
[paste the Dockerfile content here]
EOF
```

## Step 6: Build and Push from EC2

```bash
cd ~/lambda-build

# Set variables
export AWS_REGION="ap-southeast-1"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO_NAME="usdz-glb-lambda"
export IMAGE_TAG="latest"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build Docker image
docker build -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

# Tag image
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Push to ECR
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Display Image URI
echo ""
echo "✅ SUCCESS! Image URI:"
echo "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}"
```

## Step 7: Clean Up

After successful push:

```bash
# On EC2, remove build files
cd ~
rm -rf lambda-build

# From AWS Console, terminate the EC2 instance
```

## Why EC2 Works Better

- ✅ Better network connectivity
- ✅ No local Docker issues
- ✅ Faster downloads
- ✅ Clean Linux environment
- ✅ More CPU/RAM for build

## Cost

Building on t3.medium for ~15 minutes costs about $0.01 USD.
