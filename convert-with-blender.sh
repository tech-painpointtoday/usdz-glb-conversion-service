#!/bin/bash

# Convert USDZ to GLB using Blender (most reliable method)
# Blender has excellent support for both USD and glTF formats

echo "🎨 USDZ to GLB Converter using Blender"
echo "======================================="
echo ""

# Check if Blender is installed
if ! command -v blender &> /dev/null; then
    echo "❌ Blender not found"
    echo ""
    echo "Installing Blender..."
    echo "This may take a few minutes..."
    brew install --cask blender
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Blender"
        echo "Please install manually from: https://www.blender.org/download/"
        exit 1
    fi
fi

echo "✅ Blender found: $(blender --version | head -1)"
echo ""

# Check if test file exists
if [ ! -f "test.usdz" ]; then
    echo "❌ test.usdz not found"
    exit 1
fi

echo "✅ Found test.usdz"
echo ""

# Create output directory
mkdir -p test-output

# Extract USDZ to find main USD file
echo "📦 Extracting USDZ..."
unzip -q -o test.usdz -d test-output/extracted

# Find main USD file
MAIN_USD=$(find test-output/extracted -name "*.usda" | head -1)

if [ -z "$MAIN_USD" ]; then
    echo "❌ No USD file found"
    exit 1
fi

echo "✅ Found USD file: $(basename $MAIN_USD)"
echo ""

# Create Blender Python script for conversion (compatible with Blender 5.0+)
cat > test-output/convert.py << 'EOF'
import bpy
import sys
import os

# Clear default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Get file paths from command line
usd_file = sys.argv[-2]
glb_file = sys.argv[-1]

print(f"Importing USD: {usd_file}")

# Import USD
try:
    bpy.ops.wm.usd_import(filepath=usd_file)
    print("✅ USD imported successfully")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

print(f"Exporting GLB: {glb_file}")

# Export as GLB (parameters for Blender 5.0+)
try:
    bpy.ops.export_scene.gltf(
        filepath=glb_file,
        export_format='GLB',
        export_materials='EXPORT'
    )
    print("✅ Conversion complete!")
except Exception as e:
    print(f"❌ Export error: {e}")
    sys.exit(1)
EOF

# Run Blender in background mode
echo "🔄 Converting with Blender..."
echo "This may take 30-60 seconds..."
echo ""

blender --background --python test-output/convert.py -- "$MAIN_USD" "$(pwd)/test-output/test.glb" 2>&1 | grep -E "(Importing|Exporting|✅|❌|Error)"

if [ -f "test-output/test.glb" ]; then
    echo ""
    echo "✅✅✅ SUCCESS! ✅✅✅"
    echo ""
    echo "GLB file created: test-output/test.glb"
    FILE_SIZE=$(du -h test-output/test.glb | cut -f1)
    echo "File size: $FILE_SIZE"
    echo ""
    ls -lh test-output/test.glb
    echo ""
    echo "🎉 The conversion works! You can now:"
    echo "1. Open test-output/test.glb in any 3D viewer"
    echo "2. Upload to your backend/S3"
    echo "3. Use in web applications (Three.js, Babylon.js, etc.)"
    echo ""
    echo "Next: We can create a backend service using Blender for automatic conversion"
else
    echo ""
    echo "❌ Conversion failed"
    echo "Check the Blender output above for errors"
fi

# Clean up
rm -rf test-output/extracted test-output/convert.py
