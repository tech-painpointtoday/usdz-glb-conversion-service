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
        key = event['Records'][0]['s3']['object']['key'].strip()  # Remove trailing spaces
        
        print(f"Bucket: {bucket}")
        print(f"Key: {key}")
        
        # Check if USDZ file
        if not key.lower().endswith('.usdz'):
            print(f"File is not USDZ, skipping: {key}")
            return {'statusCode': 200, 'body': json.dumps('Not a USDZ file')}
        
        print(f"Processing USDZ file: {bucket}/{key}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            usdz_path = os.path.join(temp_dir, 'input.usdz')
            glb_path = os.path.join(temp_dir, 'output.glb')
            
            print(f"Downloading from S3: s3://{bucket}/{key}")
            
            # Download USDZ
            try:
                s3_client.download_file(bucket, key, usdz_path)
                file_size = os.path.getsize(usdz_path)
                print(f"✅ Downloaded USDZ file ({file_size} bytes)")
            except Exception as e:
                print(f"❌ Failed to download file: {str(e)}")
                raise
            
            # Check if gltf-transform is available
            print("Checking gltf-transform availability...")
            check_result = subprocess.run(
                ['which', 'gltf-transform'],
                capture_output=True,
                text=True
            )
            print(f"gltf-transform location: {check_result.stdout.strip()}")
            
            if check_result.returncode != 0:
                raise Exception("gltf-transform not found in container")
            
            # Convert using gltf-transform
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
            
            # Check if GLB file was created
            if not os.path.exists(glb_path):
                raise Exception(f"GLB file was not created at {glb_path}")
            
            glb_size = os.path.getsize(glb_path)
            print(f"✅ GLB file created ({glb_size} bytes)")
            
            # Upload GLB
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
