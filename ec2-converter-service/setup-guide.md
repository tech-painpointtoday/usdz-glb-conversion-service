# EC2 USDZ to GLB Conversion Service Setup Guide

This guide will help you set up an automated USDZ to GLB conversion service on EC2.

## Overview

**What it does:**
- Monitors your S3 bucket for new USDZ files
- Automatically converts them to GLB using Blender
- Uploads GLB files back to S3
- Runs 24/7 with automatic restart on failure

**Cost:** ~$7/month (t3.micro instance)

---

## Step 1: Launch EC2 Instance (5 minutes)

### 1.1 Go to EC2 Console
- Open: https://console.aws.amazon.com/ec2
- Click **Launch Instance**

### 1.2 Configure Instance
- **Name:** `usdz-glb-converter`
- **AMI:** Ubuntu Server 24.04 LTS (free tier eligible)
- **Instance type:** t3.micro (1GB RAM, sufficient for conversions)
- **Key pair:** Create new or use existing
- **Security group:** 
  - Allow SSH (port 22) from "My IP"
  - No other ports needed
- **Storage:** 30 GB gp3 (default is fine)

### 1.3 Advanced Details (Important!)
Under **Advanced details** → **IAM instance profile**:
- If you don't have one, we'll create it in Step 2
- Otherwise select one with S3 read/write access

### 1.4 Launch
Click **Launch instance**

---

## Step 2: Create IAM Role for EC2 (if needed)

If you don't have an IAM role with S3 access:

### 2.1 Go to IAM Console
- Open: https://console.aws.amazon.com/iam
- Click **Roles** → **Create role**

### 2.2 Configure Role
- **Trusted entity:** AWS service
- **Use case:** EC2
- Click **Next**

### 2.3 Add Permissions
Search and add:
- `AmazonS3FullAccess` (or create custom policy for your bucket only)

### 2.4 Name and Create
- **Role name:** `EC2-USDZ-Converter-Role`
- Click **Create role**

### 2.5 Attach to EC2
- Go back to EC2 Console
- Select your instance
- **Actions** → **Security** → **Modify IAM role**
- Select `EC2-USDZ-Converter-Role`
- Click **Update IAM role**

---

## Step 3: Connect to EC2

### Option A: EC2 Instance Connect (Easiest)
1. Select your instance in EC2 Console
2. Click **Connect**
3. Click **Connect** (opens terminal in browser)

### Option B: SSH
```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@YOUR-EC2-PUBLIC-IP
```

---

## Step 4: Install Dependencies (10 minutes)

Copy and paste these commands one by one:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv unzip

# Install AWS CLI
sudo apt install -y awscli

# Install Blender
sudo apt install -y blender

# Verify installations
python3 --version
blender --version
aws --version
```

---

## Step 5: Create Converter Service (5 minutes)

### 5.1 Create Working Directory
```bash
mkdir -p ~/usdz-converter
cd ~/usdz-converter
```

### 5.2 Create Python Script

Copy the entire script (I'll provide this separately)

### 5.3 Create Systemd Service

Copy the service file (I'll provide this separately)

### 5.4 Set Permissions
```bash
chmod +x ~/usdz-converter/converter.py
sudo chmod 644 /etc/systemd/system/usdz-converter.service
```

---

## Step 6: Configure and Start Service

### 6.1 Enable Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable usdz-converter
sudo systemctl start usdz-converter
```

### 6.2 Check Status
```bash
sudo systemctl status usdz-converter
```

Should show: **Active: active (running)**

### 6.3 View Logs
```bash
# Real-time logs
sudo journalctl -u usdz-converter -f

# Last 50 lines
sudo journalctl -u usdz-converter -n 50
```

---

## Step 7: Test the Service

### 7.1 Upload Test USDZ to S3
```bash
# From your Mac
cd ~/Desktop/usdz-glb-lamda
aws s3 cp test.usdz s3://your-home/staging/floor-plan/test-conversion.usdz
```

### 7.2 Watch Logs on EC2
```bash
sudo journalctl -u usdz-converter -f
```

You should see:
```
✅ Found new USDZ: test-conversion.usdz
🔄 Converting...
✅ GLB created: test-conversion.glb
⬆️ Uploaded to S3
```

### 7.3 Verify GLB in S3
```bash
aws s3 ls s3://your-home/staging/floor-plan/ | grep glb
```

---

## Configuration

Edit `~/usdz-converter/config.py`:

```python
# S3 Configuration
S3_BUCKET = "your-home"
S3_PREFIX = "staging/floor-plan/"

# Processing Options
CHECK_INTERVAL = 30  # Check for new files every 30 seconds
DELETE_USDZ_AFTER = False  # Keep original USDZ files
```

After changing config:
```bash
sudo systemctl restart usdz-converter
```

---

## Troubleshooting

### Service Not Starting
```bash
# Check for errors
sudo journalctl -u usdz-converter -n 50

# Check script syntax
python3 ~/usdz-converter/converter.py --test
```

### Permission Errors
```bash
# Verify IAM role
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://your-home/staging/floor-plan/
```

### Blender Errors
```bash
# Test Blender manually
blender --version
blender --background --python ~/usdz-converter/test_blender.py
```

---

## Maintenance

### View Logs
```bash
sudo journalctl -u usdz-converter -f
```

### Restart Service
```bash
sudo systemctl restart usdz-converter
```

### Stop Service
```bash
sudo systemctl stop usdz-converter
```

### Update Script
1. Edit `~/usdz-converter/converter.py`
2. Restart: `sudo systemctl restart usdz-converter`

---

## Cost Breakdown

- **EC2 t3.micro:** ~$7/month (730 hours × $0.0104/hour)
- **Storage (30GB):** ~$3/month
- **Data transfer:** Minimal (usually free tier)
- **Total:** ~$10/month

---

## Next Steps

Once working:
1. ✅ Monitor logs for first few days
2. ✅ Adjust CHECK_INTERVAL if needed
3. ✅ Set up CloudWatch alarms (optional)
4. ✅ Create AMI backup of configured instance

---

## Files Included

- `converter.py` - Main conversion script
- `usdz-converter.service` - Systemd service file
- `config.py` - Configuration file
- `install.sh` - Automated setup script
