# 🚀 QUICK START - EC2 USDZ to GLB Converter

## What You'll Get

✅ Automatic USDZ → GLB conversion
✅ Monitors S3 bucket 24/7
✅ Runs in background
✅ Auto-restarts on failure
✅ Costs ~$10/month

---

## Setup (30 minutes)

### 1. Launch EC2 (5 min)
- Go to EC2 Console → Launch Instance
- **AMI:** Ubuntu 24.04 LTS
- **Type:** t3.micro
- **Storage:** 30 GB
- **Key pair:** Create/select one
- Launch!

### 2. Create IAM Role (5 min)
- IAM Console → Roles → Create role
- **Service:** EC2
- **Permission:** AmazonS3FullAccess
- **Name:** EC2-USDZ-Converter-Role
- Attach to EC2: Instance → Actions → Security → Modify IAM role

### 3. Connect to EC2
- Select instance → Click "Connect"
- Use "EC2 Instance Connect"

### 4. Run Installation Commands

```bash
# Install everything
sudo apt update && sudo apt install -y python3 python3-pip unzip awscli blender
pip3 install boto3 --user

# Create directory
mkdir -p ~/usdz-converter
cd ~/usdz-converter
```

### 5. Create Files

**Create converter.py:**
```bash
nano ~/usdz-converter/converter.py
```
Paste the content from `converter.py` file, then:
- Press `Ctrl+X`
- Press `Y`
- Press `Enter`

Make it executable:
```bash
chmod +x ~/usdz-converter/converter.py
```

**Create service file:**
```bash
sudo nano /etc/systemd/system/usdz-converter.service
```
Paste the content from `usdz-converter.service`, then save (Ctrl+X, Y, Enter)

### 6. Start Service

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable usdz-converter
sudo systemctl start usdz-converter

# Check status
sudo systemctl status usdz-converter
```

Should show: `Active: active (running)` ✅

### 7. Test It!

**From your Mac:**
```bash
# Upload a test USDZ
aws s3 cp ~/Desktop/usdz-glb-lamda/test.usdz s3://your-home/staging/floor-plan/test-auto.usdz
```

**On EC2, watch logs:**
```bash
sudo journalctl -u usdz-converter -f
```

You'll see:
```
✅ Found new USDZ: test-auto.usdz
📥 Downloading...
🔄 Converting with Blender...
✅ GLB created
📤 Uploading...
✅✅✅ Successfully processed
```

**Verify GLB created:**
```bash
aws s3 ls s3://your-home/staging/floor-plan/ | grep glb
```

---

## Daily Usage

### Check if running:
```bash
sudo systemctl status usdz-converter
```

### View logs:
```bash
# Live logs
sudo journalctl -u usdz-converter -f

# Last 50 lines
sudo journalctl -u usdz-converter -n 50
```

### Restart:
```bash
sudo systemctl restart usdz-converter
```

### Stop:
```bash
sudo systemctl stop usdz-converter
```

---

## Configuration

Edit `~/usdz-converter/converter.py`:

```python
# Line 14-17
S3_BUCKET = "your-home"          # Your bucket name
S3_PREFIX = "staging/floor-plan/"  # Folder to monitor
CHECK_INTERVAL = 30               # Check every 30 seconds
DELETE_USDZ_AFTER = False         # Keep original files
```

After editing:
```bash
sudo systemctl restart usdz-converter
```

---

## Troubleshooting

**Service not running:**
```bash
sudo journalctl -u usdz-converter -n 50
```

**S3 access denied:**
- Check IAM role is attached to EC2
- Test: `aws s3 ls s3://your-home/`

**Blender not found:**
```bash
which blender
# Should show: /usr/bin/blender
```

---

## How It Works

1. **Service checks S3 every 30 seconds**
2. **Finds new .usdz files**
3. **Downloads to EC2**
4. **Extracts USDZ (it's a ZIP)**
5. **Finds USD file inside**
6. **Runs Blender conversion**
7. **Uploads .glb back to S3**
8. **Remembers processed files** (won't re-process)

---

## Files Created

```
~/usdz-converter/
├── converter.py          # Main script
└── /tmp/usdz-converter/
    └── processed.txt     # History of processed files

/etc/systemd/system/
└── usdz-converter.service  # System service

/var/log/
└── usdz-converter.log     # Log file
```

---

## Cost

- **EC2 t3.micro:** $7.59/month (730h × $0.0104/h)
- **30GB Storage:** $3/month
- **Data transfer:** Usually free
- **Total:** ~$10/month

---

## Next Steps

1. ✅ Monitor for a day to ensure it's working
2. ✅ Adjust CHECK_INTERVAL if needed (30s is good default)
3. ✅ Set up CloudWatch alarm (optional)
4. ✅ Create AMI backup once configured

---

## Support

**View all logs since start:**
```bash
sudo journalctl -u usdz-converter --no-pager
```

**Check service configuration:**
```bash
sudo systemctl cat usdz-converter
```

**Manually run conversion (for testing):**
```bash
cd ~/usdz-converter
python3 converter.py
```
Press Ctrl+C to stop.

---

That's it! Your automatic USDZ → GLB converter is now running 24/7! 🎉
