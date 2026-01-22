#!/bin/bash

# Test USDZ to GLB conversion locally
# This will verify the conversion works before deploying to Lambda

echo "🧪 Testing USDZ to GLB Conversion Locally"
echo "=========================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Installing..."
    echo "Please install Node.js first:"
    echo "  brew install node"
    exit 1
fi

echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"
echo ""

# Check if gltf-transform is installed
if ! command -v gltf-transform &> /dev/null; then
    echo "📦 gltf-transform not found. Installing..."
    npm install -g @gltf-transform/cli
    echo ""
fi

echo "✅ gltf-transform version: $(gltf-transform --version)"
echo ""

# Create test directory
mkdir -p test-output

echo "📝 Instructions:"
echo "1. Place a USDZ file in this directory"
echo "2. Name it 'test.usdz'"
echo "3. Run this script again"
echo ""

# Check if test file exists
if [ ! -f "test.usdz" ]; then
    echo "❌ test.usdz not found"
    echo ""
    echo "Please copy a USDZ file to this directory and name it 'test.usdz'"
    echo "Then run: ./test-conversion-locally.sh"
    exit 1
fi

echo "✅ Found test.usdz"
FILE_SIZE=$(du -h test.usdz | cut -f1)
echo "   File size: $FILE_SIZE"
echo ""

# Convert USDZ to GLB
echo "🔄 Converting USDZ to GLB..."
gltf-transform copy test.usdz test-output/test.glb

if [ $? -eq 0 ]; then
    echo ""
    echo "✅✅✅ SUCCESS! ✅✅✅"
    echo ""
    echo "GLB file created: test-output/test.glb"
    OUTPUT_SIZE=$(du -h test-output/test.glb | cut -f1)
    echo "Output size: $OUTPUT_SIZE"
    echo ""
    echo "🎉 The conversion works! Now you can deploy to Lambda with confidence."
    echo ""
    ls -lh test-output/
else
    echo ""
    echo "❌ CONVERSION FAILED"
    echo ""
    echo "The conversion didn't work. This means:"
    echo "1. gltf-transform might not support USDZ format"
    echo "2. The USDZ file might be corrupted"
    echo "3. We need a different conversion approach"
    echo ""
    echo "Let's investigate before deploying to Lambda."
fi
