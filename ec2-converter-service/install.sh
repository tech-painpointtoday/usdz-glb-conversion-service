#!/bin/bash

# Automated installation script for USDZ to GLB Conversion Service
# Run this on your EC2 instance after connecting

set -e

echo "🚀 USDZ to GLB Conversion Service Installer"
echo "============================================"
echo ""

# Check if running as ubuntu user
if [ "$USER" != "ubuntu" ]; then
    echo "⚠️  Please run as ubuntu user"
    echo "   Switch with: sudo su - ubuntu"
    exit 1
fi

# Update system
echo "📦 Step 1: Updating system..."
sudo apt update -y

# Install dependencies
echo "📦 Step 2: Installing dependencies..."
sudo apt install -y python3 python3-pip python3-venv unzip awscli blender

# Install Python packages
echo "📦 Step 3: Installing Python packages..."
pip3 install boto3 --user

# Create working directory
echo "📁 Step 4: Creating working directory..."
mkdir -p ~/usdz-converter
cd ~/usdz-converter

# Copy converter script
echo "📝 Step 5: Creating converter script..."
cat > ~/usdz-converter/converter.py << 'SCRIPT_END'
[PASTE THE converter.py CONTENT HERE]
SCRIPT_END

chmod +x ~/usdz-converter/converter.py

# Create systemd service
echo "⚙️  Step 6: Creating systemd service..."
sudo tee /etc/systemd/system/usdz-converter.service > /dev/null << 'SERVICE_END'
[Unit]
Description=USDZ to GLB Conversion Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/usdz-converter
ExecStart=/usr/bin/python3 /home/ubuntu/usdz-converter/converter.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
SERVICE_END

# Create log directory
sudo mkdir -p /var/log
sudo touch /var/log/usdz-converter.log
sudo chown ubuntu:ubuntu /var/log/usdz-converter.log

# Reload systemd
echo "🔄 Step 7: Configuring service..."
sudo systemctl daemon-reload
sudo systemctl enable usdz-converter

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit configuration if needed:"
echo "   nano ~/usdz-converter/converter.py"
echo "   (Update S3_BUCKET and S3_PREFIX)"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl start usdz-converter"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status usdz-converter"
echo ""
echo "4. View logs:"
echo "   sudo journalctl -u usdz-converter -f"
echo ""
