#!/usr/bin/env python3

"""
USDZ to GLB Conversion Service
Monitors S3 bucket for new USDZ files and converts them to GLB using Blender
"""

import os
import sys
import time
import subprocess
import tempfile
import logging
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

# Configuration
S3_BUCKET = "your-home"
S3_PREFIX = "staging/floor-plan/"
CHECK_INTERVAL = 30  # seconds
TEMP_DIR = "/tmp/usdz-converter"
DELETE_USDZ_AFTER = False  # Set to True to delete USDZ after conversion

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/usdz-converter.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = boto3.client('s3', region_name='ap-southeast-1')

# Create temp directory
os.makedirs(TEMP_DIR, exist_ok=True)

class USDZConverter:
    def __init__(self):
        self.processed_files = set()
        self.load_processed_files()
    
    def load_processed_files(self):
        """Load list of already processed files"""
        processed_file = Path(TEMP_DIR) / 'processed.txt'
        if processed_file.exists():
            with open(processed_file, 'r') as f:
                self.processed_files = set(line.strip() for line in f)
            logger.info(f"Loaded {len(self.processed_files)} processed files from history")
    
    def save_processed_file(self, key):
        """Save processed file to history"""
        self.processed_files.add(key)
        processed_file = Path(TEMP_DIR) / 'processed.txt'
        with open(processed_file, 'a') as f:
            f.write(f"{key}\n")
    
    def list_usdz_files(self):
        """List all USDZ files in S3 bucket"""
        try:
            response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=S3_PREFIX
            )
            
            if 'Contents' not in response:
                return []
            
            usdz_files = [
                obj['Key'] for obj in response['Contents']
                if obj['Key'].lower().endswith('.usdz')
            ]
            
            return usdz_files
        except ClientError as e:
            logger.error(f"Error listing S3 objects: {e}")
            return []
    
    def download_from_s3(self, key, local_path):
        """Download file from S3"""
        try:
            logger.info(f"📥 Downloading: {key}")
            s3_client.download_file(S3_BUCKET, key, local_path)
            file_size = os.path.getsize(local_path)
            logger.info(f"✅ Downloaded {file_size} bytes")
            return True
        except ClientError as e:
            logger.error(f"❌ Download failed: {e}")
            return False
    
    def upload_to_s3(self, local_path, key):
        """Upload file to S3"""
        try:
            logger.info(f"📤 Uploading: {key}")
            s3_client.upload_file(
                local_path,
                S3_BUCKET,
                key,
                ExtraArgs={'ContentType': 'model/gltf-binary'}
            )
            logger.info(f"✅ Uploaded to S3: {key}")
            return True
        except ClientError as e:
            logger.error(f"❌ Upload failed: {e}")
            return False
    
    def convert_usdz_to_glb(self, usdz_path, glb_path):
        """Convert USDZ to GLB using Blender"""
        try:
            # Extract USDZ (it's a ZIP file)
            extract_dir = tempfile.mkdtemp(dir=TEMP_DIR)
            logger.info(f"📦 Extracting USDZ...")
            
            subprocess.run(
                ['unzip', '-q', '-o', usdz_path, '-d', extract_dir],
                check=True,
                capture_output=True
            )
            
            # Find main USD file
            usd_files = list(Path(extract_dir).rglob('*.usda'))
            if not usd_files:
                usd_files = list(Path(extract_dir).rglob('*.usdc'))
            
            if not usd_files:
                logger.error("❌ No USD file found in USDZ")
                return False
            
            main_usd = str(usd_files[0])
            logger.info(f"✅ Found USD: {Path(main_usd).name}")
            
            # Create Blender conversion script
            blender_script = Path(TEMP_DIR) / 'convert_temp.py'
            with open(blender_script, 'w') as f:
                f.write(f"""
import bpy
import sys

# Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import USD
usd_file = '{main_usd}'
glb_file = '{glb_path}'

print(f"Importing: {{usd_file}}")
bpy.ops.wm.usd_import(filepath=usd_file)

print(f"Exporting: {{glb_file}}")
bpy.ops.export_scene.gltf(
    filepath=glb_file,
    export_format='GLB',
    export_materials='EXPORT'
)

print("✅ Conversion complete")
""")
            
            # Run Blender conversion
            logger.info(f"🔄 Converting with Blender...")
            result = subprocess.run(
                ['blender', '--background', '--python', str(blender_script)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Check if GLB was created
            if os.path.exists(glb_path):
                file_size = os.path.getsize(glb_path)
                logger.info(f"✅ GLB created ({file_size} bytes)")
                
                # Clean up
                subprocess.run(['rm', '-rf', extract_dir], check=False)
                os.remove(blender_script)
                
                return True
            else:
                logger.error(f"❌ GLB file not created")
                logger.error(f"Blender output: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Conversion timeout (>5 minutes)")
            return False
        except Exception as e:
            logger.error(f"❌ Conversion error: {e}")
            return False
    
    def process_file(self, usdz_key):
        """Process a single USDZ file"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 Processing: {usdz_key}")
        logger.info(f"{'='*60}")
        
        # Create temp file paths
        usdz_filename = Path(usdz_key).name
        glb_filename = usdz_filename.rsplit('.', 1)[0] + '.glb'
        glb_key = usdz_key.rsplit('.', 1)[0] + '.glb'
        
        usdz_temp = os.path.join(TEMP_DIR, usdz_filename)
        glb_temp = os.path.join(TEMP_DIR, glb_filename)
        
        try:
            # Download USDZ
            if not self.download_from_s3(usdz_key, usdz_temp):
                return False
            
            # Convert to GLB
            if not self.convert_usdz_to_glb(usdz_temp, glb_temp):
                return False
            
            # Upload GLB
            if not self.upload_to_s3(glb_temp, glb_key):
                return False
            
            # Mark as processed
            self.save_processed_file(usdz_key)
            
            # Delete USDZ if configured
            if DELETE_USDZ_AFTER:
                try:
                    s3_client.delete_object(Bucket=S3_BUCKET, Key=usdz_key)
                    logger.info(f"🗑️ Deleted source USDZ from S3")
                except ClientError as e:
                    logger.warning(f"⚠️ Could not delete USDZ: {e}")
            
            logger.info(f"✅✅✅ Successfully processed: {usdz_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            return False
        finally:
            # Clean up temp files
            for temp_file in [usdz_temp, glb_temp]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    
    def run(self):
        """Main loop - monitor and process files"""
        logger.info("🚀 USDZ to GLB Conversion Service Started")
        logger.info(f"📦 Monitoring: s3://{S3_BUCKET}/{S3_PREFIX}")
        logger.info(f"⏱️ Check interval: {CHECK_INTERVAL}s")
        logger.info(f"{'='*60}\n")
        
        while True:
            try:
                # List USDZ files
                usdz_files = self.list_usdz_files()
                
                # Find new files
                new_files = [
                    f for f in usdz_files
                    if f not in self.processed_files
                ]
                
                if new_files:
                    logger.info(f"📋 Found {len(new_files)} new USDZ file(s)")
                    
                    for usdz_key in new_files:
                        self.process_file(usdz_key)
                        time.sleep(2)  # Small delay between files
                
                # Wait before next check
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Service stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                time.sleep(CHECK_INTERVAL)

def main():
    """Main entry point"""
    converter = USDZConverter()
    converter.run()

if __name__ == '__main__':
    main()
