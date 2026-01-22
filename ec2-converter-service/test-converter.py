#!/usr/bin/env python3

"""
USDZ to GLB Test Converter
Usage: python3 test-converter.py <s3-key>
Example: python3 test-converter.py staging/floor-plan/test-auto.usdz
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
TEMP_DIR = os.path.expanduser("~/usdz-converter-test")
CONVERSION_TIMEOUT = 1800  # 30 minutes

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = boto3.client('s3', region_name='ap-southeast-1')

# Create temp directory
os.makedirs(TEMP_DIR, exist_ok=True)

def download_from_s3(key, local_path):
    """Download file from S3"""
    try:
        logger.info(f"📥 Downloading: {key}")
        logger.info(f"   From bucket: {S3_BUCKET}")
        s3_client.download_file(S3_BUCKET, key, local_path)
        file_size = os.path.getsize(local_path)
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"✅ Downloaded {file_size:,} bytes ({file_size_mb:.2f} MB)")
        return True
    except ClientError as e:
        logger.error(f"❌ Download failed: {e}")
        return False

def upload_to_s3(local_path, key):
    """Upload file to S3"""
    try:
        file_size = os.path.getsize(local_path)
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"📤 Uploading: {key}")
        logger.info(f"   Size: {file_size_mb:.2f} MB")
        
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

def convert_usdz_to_glb(usdz_path, glb_path):
    """Convert USDZ to GLB using Blender"""
    start_time = time.time()
    
    try:
        # Extract USDZ (it's a ZIP file)
        extract_dir = tempfile.mkdtemp(dir=TEMP_DIR)
        logger.info(f"📦 Extracting USDZ...")
        logger.info(f"   To: {extract_dir}")
        
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
            logger.info(f"   Contents of {extract_dir}:")
            for item in Path(extract_dir).rglob('*'):
                logger.info(f"   - {item}")
            return False
        
        main_usd = str(usd_files[0])
        usd_size = os.path.getsize(main_usd) / (1024 * 1024)
        logger.info(f"✅ Found USD: {Path(main_usd).name} ({usd_size:.2f} MB)")
        
        # Create Blender conversion script
        blender_script = Path(TEMP_DIR) / f'convert_test_{os.getpid()}.py'
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
        
        logger.info(f"   Script: {blender_script}")
        
        # Run Blender conversion
        logger.info(f"🔄 Converting with Blender...")
        logger.info(f"   Timeout: {CONVERSION_TIMEOUT}s ({CONVERSION_TIMEOUT//60} minutes)")
        logger.info(f"   Started at: {time.strftime('%H:%M:%S')}")
        logger.info(f"   This may take several minutes for large files...")
        
        conversion_start = time.time()
        
        # Run Blender and show output in real-time
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
        
        logger.info(f"   Blender finished in {conversion_time:.1f}s")
        logger.info(f"   Exit code: {process.returncode}")
        
        # Check if GLB was created
        if os.path.exists(glb_path):
            file_size = os.path.getsize(glb_path)
            if file_size > 0:
                file_size_mb = file_size / (1024 * 1024)
                total_time = time.time() - start_time
                logger.info(f"✅ GLB created successfully!")
                logger.info(f"   Size: {file_size:,} bytes ({file_size_mb:.2f} MB)")
                logger.info(f"   Location: {glb_path}")
                logger.info(f"⏱️  Total conversion time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
                return True
            else:
                logger.error(f"❌ GLB file is empty (0 bytes)")
                return False
        else:
            logger.error(f"❌ GLB file not created")
            logger.error(f"   Expected at: {glb_path}")
            logger.info(f"\n📋 Blender output:")
            for line in blender_output:
                logger.info(f"   {line}")
            return False
            
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        logger.error(f"❌ Conversion timeout after {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        logger.error(f"   File may be too large or complex")
        return False
    except Exception as e:
        logger.error(f"❌ Conversion error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 test-converter.py <s3-key>")
        print("Example: python3 test-converter.py staging/floor-plan/test-auto.usdz")
        sys.exit(1)
    
    usdz_key = sys.argv[1]
    
    logger.info(f"\n{'='*70}")
    logger.info(f"🎯 USDZ to GLB Test Converter")
    logger.info(f"{'='*70}")
    logger.info(f"📦 Bucket: {S3_BUCKET}")
    logger.info(f"📄 File: {usdz_key}")
    logger.info(f"{'='*70}\n")
    
    # Validate S3 key
    if not usdz_key.lower().endswith('.usdz'):
        logger.error("❌ File must be a .usdz file")
        sys.exit(1)
    
    # Create temp file paths
    usdz_filename = Path(usdz_key).name
    glb_filename = usdz_filename.rsplit('.', 1)[0] + '.glb'
    glb_key = usdz_key.rsplit('.', 1)[0] + '.glb'
    
    usdz_temp = os.path.join(TEMP_DIR, usdz_filename)
    glb_temp = os.path.join(TEMP_DIR, glb_filename)
    
    logger.info(f"📁 Temporary files:")
    logger.info(f"   USDZ: {usdz_temp}")
    logger.info(f"   GLB:  {glb_temp}\n")
    
    process_start = time.time()
    
    try:
        # Step 1: Download USDZ
        logger.info("STEP 1/3: Download from S3")
        logger.info("-" * 70)
        if not download_from_s3(usdz_key, usdz_temp):
            logger.error("❌ Download failed")
            sys.exit(1)
        print()
        
        # Step 2: Convert to GLB
        logger.info("STEP 2/3: Convert USDZ to GLB")
        logger.info("-" * 70)
        if not convert_usdz_to_glb(usdz_temp, glb_temp):
            logger.error("❌ Conversion failed")
            logger.info(f"\n📁 Check temp files at: {TEMP_DIR}")
            sys.exit(1)
        print()
        
        # Step 3: Upload GLB
        logger.info("STEP 3/3: Upload to S3")
        logger.info("-" * 70)
        if not upload_to_s3(glb_temp, glb_key):
            logger.error("❌ Upload failed")
            sys.exit(1)
        print()
        
        # Success
        total_time = time.time() - process_start
        logger.info("=" * 70)
        logger.info("✅✅✅ CONVERSION SUCCESSFUL!")
        logger.info("=" * 70)
        logger.info(f"📥 Input:  s3://{S3_BUCKET}/{usdz_key}")
        logger.info(f"📤 Output: s3://{S3_BUCKET}/{glb_key}")
        logger.info(f"⏱️  Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        logger.info("=" * 70)
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        # Clean up temp files
        logger.info("\n🧹 Cleaning up temporary files...")
        for temp_file in [usdz_temp, glb_temp]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.info(f"   Deleted: {temp_file}")
                except:
                    pass

if __name__ == '__main__':
    main()
