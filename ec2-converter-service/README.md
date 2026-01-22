# EC2 USDZ to GLB Conversion Service

Automatic background service that monitors your S3 bucket and converts USDZ files to GLB format using Blender.

## 📁 Files in This Directory

### Documentation
- **`QUICK-START.md`** ⭐ START HERE - Step-by-step setup (30 min)
- **`setup-guide.md`** - Detailed setup guide with troubleshooting
- **`README.md`** - This file

### Service Files
- **`converter.py`** - Python script that does the conversion
- **`usdz-converter.service`** - Systemd service configuration
- **`install.sh`** - Automated installation script (optional)

## 🚀 Quick Setup

### 1. Launch EC2
- Ubuntu 24.04, t3.micro, 30GB storage

### 2. Connect & Install
```bash
# Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip unzip awscli blender
pip3 install boto3 --user

# Create directory
mkdir -p ~/usdz-converter
cd ~/usdz-converter
```

### 3. Copy Files to EC2
Upload `converter.py` and `usdz-converter.service` to your EC2 instance.

### 4. Configure & Start
```bash
# Make executable
chmod +x ~/usdz-converter/converter.py

# Install service
sudo cp usdz-converter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable usdz-converter
sudo systemctl start usdz-converter

# Check status
sudo systemctl status usdz-converter
```

## ⚙️ Configuration

Edit `converter.py` lines 14-17:

```python
S3_BUCKET = "your-home"           # Your S3 bucket name
S3_PREFIX = "staging/floor-plan/"  # Folder to monitor
CHECK_INTERVAL = 30                # Check interval in seconds
DELETE_USDZ_AFTER = False          # Keep original USDZ files
```

## 📊 How It Works

```
┌─────────────────────────────────────────────────────────┐
│  1. Service checks S3 every 30 seconds                  │
│  2. Finds new .usdz files                               │
│  3. Downloads to /tmp/usdz-converter/                   │
│  4. Extracts USDZ (ZIP archive)                         │
│  5. Finds main .usda/.usdc file                         │
│  6. Runs Blender in background mode                     │
│  7. Converts USD → GLB                                  │
│  8. Uploads .glb to same S3 location                    │
│  9. Records in processed.txt (won't reprocess)          │
│ 10. Cleans up temp files                                │
└─────────────────────────────────────────────────────────┘
```

## 💰 Cost

- **EC2 t3.micro:** ~$7.59/month
- **30GB EBS:** ~$3/month
- **Total:** ~$11/month

## 🔍 Monitoring

```bash
# Live logs
sudo journalctl -u usdz-converter -f

# Recent logs
sudo journalctl -u usdz-converter -n 50

# Service status
sudo systemctl status usdz-converter
```

## 🛠️ Maintenance

```bash
# Restart service
sudo systemctl restart usdz-converter

# Stop service
sudo systemctl stop usdz-converter

# Update script
nano ~/usdz-converter/converter.py
sudo systemctl restart usdz-converter
```

## ✅ Features

- ✅ Automatic 24/7 monitoring
- ✅ Processes new files automatically
- ✅ Remembers processed files (no duplicates)
- ✅ Auto-restarts on failure
- ✅ Detailed logging
- ✅ Configurable check interval
- ✅ Optional USDZ deletion after conversion
- ✅ Preserves original filenames

## 🎯 Example

**Upload:**
```
s3://your-home/staging/floor-plan/RoomPlan-2025-12-16T07:29:35Z.usdz
```

**Service automatically creates:**
```
s3://your-home/staging/floor-plan/RoomPlan-2025-12-16T07:29:35Z.glb
```

## 🐛 Troubleshooting

### Service won't start
```bash
# Check for errors
sudo journalctl -u usdz-converter -xe

# Test script manually
cd ~/usdz-converter
python3 converter.py
```

### Permission errors
```bash
# Verify IAM role
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://your-home/staging/floor-plan/
```

### Blender errors
```bash
# Verify Blender installation
blender --version
which blender
```

## 📚 Additional Resources

- [Blender Documentation](https://docs.blender.org/)
- [Boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [Systemd Service Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)

## 🎉 Success!

Once set up, your service will:
- Monitor S3 continuously
- Convert files automatically
- Log all activities
- Restart on failure
- Run 24/7 reliably

**No more manual conversions needed!** 🚀
