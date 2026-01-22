#!/usr/bin/env python3

"""
USDZ to GLB Conversion Service
Monitors S3 bucket for new USDZ files and converts them to GLB using Blender
TESTED AND WORKING - Based on test-converter.py
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
TEMP_DIR = os.path.expanduser("~/usdz-converter")
PROCESSED_LOG = os.path.join(TEMP_DIR, "processed.txt")
DELETE_USDZ_AFTER = False
CONVERSION_TIMEOUT = 1800  # 30 minutes
MAX_FILE_SIZE_MB = 500  # Warning threshold

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(TEMP_DIR, 'converter.log'))
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
        if os.path.exists(PROCESSED_LOG):
            with open(PROCESSED_LOG, 'r') as f:
                self.processed_files = set(line.strip() for line in f)
            logger.info(f"Loaded {len(self.processed_files)} processed files from history")
    
    def save_processed_file(self, key):
        """Save processed file to history"""
        self.processed_files.add(key)
        with open(PROCESSED_LOG, 'a') as f:
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
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"✅ Downloaded {file_size:,} bytes ({file_size_mb:.2f} MB)")
            
            if file_size_mb > MAX_FILE_SIZE_MB:
                logger.warning(f"⚠️  Large file: {file_size_mb:.2f} MB - conversion may take 10+ minutes")
            elif file_size_mb > 100:
                logger.info(f"⏱️  Large file detected - estimated conversion time: 5-10 minutes")
            
            return True
        except ClientError as e:
            logger.error(f"❌ Download failed: {e}")
            return False
    
    def upload_to_s3(self, local_path, key):
        """Upload file to S3"""
        try:
            file_size = os.path.getsize(local_path)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"📤 Uploading: {key} ({file_size_mb:.2f} MB)")
            
            s3_client.upload_file(
                local_path,
                S3_BUCKET,
                key,
                ExtraArgs={'ContentType': 'model/gltf-binary'}
            )
            logger.info(f"✅ Uploaded to S3: s3://{S3_BUCKET}/{key}")
            return True
        except ClientError as e:
            logger.error(f"❌ Upload failed: {e}")
            return False
    
    def convert_usdz_to_glb(self, usdz_path, glb_path):
        """Convert USDZ to GLB using Blender - TESTED AND WORKING"""
        start_time = time.time()
        
        try:
            # Extract USDZ (it's a ZIP file)
            extract_dir = tempfile.mkdtemp(dir=TEMP_DIR)
            logger.info(f"📦 Extracting USDZ to: {extract_dir}")
            
            result = subprocess.run(
                ['unzip', '-q', '-o', usdz_path, '-d', extract_dir],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Extraction failed: {result.stderr}")
                return False
            
            extraction_time = time.time() - start_time
            logger.info(f"✅ Extracted in {extraction_time:.1f} seconds")
            
            # Find main USD file
            usd_files = list(Path(extract_dir).rglob('*.usda'))
            if not usd_files:
                usd_files = list(Path(extract_dir).rglob('*.usdc'))
            
            if not usd_files:
                logger.error("❌ No USD file found in USDZ")
                return False
            
            main_usd = str(usd_files[0])
            usd_size = os.path.getsize(main_usd) / (1024 * 1024)
            logger.info(f"✅ Found USD: {Path(main_usd).name} ({usd_size:.2f} MB)")
            
            # Create Blender conversion script
            blender_script = Path(TEMP_DIR) / f'convert_{os.getpid()}.py'
            script_content = '''
import bpy
import sys
import traceback
import time

start = time.time()

try:
    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    usd_file = r"''' + main_usd + '''"
    glb_file = r"''' + glb_path + '''"
    
    print(f"[{time.time()-start:.1f}s] Importing USD: {usd_file}")
    
    # Import USD
    bpy.ops.wm.usd_import(filepath=usd_file)
    
    print(f"[{time.time()-start:.1f}s] Import complete")
    
    # Check if anything was imported
    if len(bpy.data.objects) == 0:
        print("ERROR: No objects imported from USD")
        sys.exit(1)
    
    print(f"[{time.time()-start:.1f}s] Imported {len(bpy.data.objects)} objects")
    print(f"[{time.time()-start:.1f}s] Exporting GLB: {glb_file}")
    
    # Export as GLB
    bpy.ops.export_scene.gltf(
        filepath=glb_file,
        export_format='GLB'
    )
    
    elapsed = time.time() - start
    print(f"[{elapsed:.1f}s] SUCCESS: Conversion complete")
    sys.exit(0)
    
except Exception as e:
    elapsed = time.time() - start
    print(f"[{elapsed:.1f}s] ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
'''
            
            with open(blender_script, 'w') as f:
                f.write(script_content)
            
            # Run Blender conversion
            logger.info(f"🔄 Converting with Blender (timeout: {CONVERSION_TIMEOUT}s / {CONVERSION_TIMEOUT//60} minutes)...")
            logger.info(f"⏱️  Started at: {time.strftime('%H:%M:%S')}")
            
            conversion_start = time.time()
            
            # Run Blender and capture output
            process = subprocess.Popen(
                ['blender', '--background', '--python', str(blender_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Print output as it comes
            blender_output = []
            for line in process.stdout:
                line = line.strip()
                if line:
                    blender_output.append(line)
                    # Show progress lines
                    if any(x in line for x in ['[', 's]', 'SUCCESS', 'ERROR', 'Imported', 'Exporting']):
                        logger.info(f"   Blender: {line}")
            
            process.wait(timeout=CONVERSION_TIMEOUT)
            conversion_time = time.time() - conversion_start
            
            # Clean up extract directory
            subprocess.run(['rm', '-rf', extract_dir], check=False)
            if blender_script.exists():
                blender_script.unlink()
            
            # Check if GLB was created
            if os.path.exists(glb_path) and os.path.getsize(glb_path) > 0:
                file_size = os.path.getsize(glb_path)
                file_size_mb = file_size / (1024 * 1024)
                total_time = time.time() - start_time
                logger.info(f"✅ GLB created: {file_size:,} bytes ({file_size_mb:.2f} MB)")
                logger.info(f"⏱️  Total conversion time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
                return True
            else:
                logger.error(f"❌ GLB file not created or empty")
                logger.error(f"Blender exit code: {process.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            logger.error(f"❌ Conversion timeout after {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
            logger.error(f"   File may be too large or complex for this instance")
            return False
        except Exception as e:
            logger.error(f"❌ Conversion error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def process_file(self, usdz_key):
        """Process a single USDZ file"""
        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 Processing: {usdz_key}")
        logger.info(f"{'='*70}")
        
        # Create temp file paths - PRESERVE ORIGINAL FILENAME
        usdz_filename = Path(usdz_key).name
        glb_filename = usdz_filename.rsplit('.', 1)[0] + '.glb'
        glb_key = usdz_key.rsplit('.', 1)[0] + '.glb'
        
        usdz_temp = os.path.join(TEMP_DIR, usdz_filename)
        glb_temp = os.path.join(TEMP_DIR, glb_filename)
        
        process_start = time.time()
        
        try:
            # Step 1: Download USDZ
            if not self.download_from_s3(usdz_key, usdz_temp):
                return False
            
            # Step 2: Convert to GLB
            if not self.convert_usdz_to_glb(usdz_temp, glb_temp):
                return False
            
            # Step 3: Upload GLB
            if not self.upload_to_s3(glb_temp, glb_key):
                return False
            
            # Mark as processed
            self.save_processed_file(usdz_key)
            
            # Delete USDZ if configured
            if DELETE_USDZ_AFTER:
                try:
                    s3_client.delete_object(Bucket=S3_BUCKET, Key=usdz_key)
                    logger.info(f"🗑️  Deleted source USDZ from S3")
                except ClientError as e:
                    logger.warning(f"⚠️  Could not delete USDZ: {e}")
            
            total_time = time.time() - process_start
            logger.info(f"{'='*70}")
            logger.info(f"✅✅✅ Successfully processed: {usdz_key}")
            logger.info(f"📤 Output: {glb_key}")
            logger.info(f"⏱️  Total processing time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
            logger.info(f"{'='*70}\n")
            return True
            
        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        finally:
            # Clean up temp files
            for temp_file in [usdz_temp, glb_temp]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
    
    def run(self):
        """Main loop - monitor and process files"""
        logger.info("🚀 USDZ to GLB Conversion Service Started")
        logger.info(f"📦 Monitoring: s3://{S3_BUCKET}/{S3_PREFIX}")
        logger.info(f"⏱️  Check interval: {CHECK_INTERVAL}s")
        logger.info(f"⏱️  Conversion timeout: {CONVERSION_TIMEOUT}s ({CONVERSION_TIMEOUT//60} minutes)")
        logger.info(f"⚠️  Large file warning threshold: {MAX_FILE_SIZE_MB} MB")
        logger.info(f"📁 Working directory: {TEMP_DIR}")
        logger.info(f"📝 Processed files log: {PROCESSED_LOG}")
        logger.info(f"{'='*70}\n")
        
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
                        success = self.process_file(usdz_key)
                        if success:
                            logger.info(f"✅ Conversion successful for {usdz_key}")
                        else:
                            logger.error(f"❌ Conversion failed for {usdz_key}")
                            # Still mark as processed to avoid infinite retry
                            self.save_processed_file(usdz_key)
                        
                        time.sleep(2)  # Small delay between files
                else:
                    logger.info(f"No new USDZ files. Next check in {CHECK_INTERVAL}s...")
                
                # Wait before next check
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Service stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error in main loop: {e}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(CHECK_INTERVAL)

def main():
    """Main entry point"""
    logger.info(f"Starting converter service...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    converter = USDZConverter()
    converter.run()

if __name__ == '__main__':
    main()
