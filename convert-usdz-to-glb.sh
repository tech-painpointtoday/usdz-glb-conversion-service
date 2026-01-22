#!/bin/bash

# Convert USDZ to GLB using Apple's USD tools + Python usd2gltf
# This is the proper way to convert USDZ to GLB

echo "🔄 USDZ to GLB Converter"
echo "========================"
echo ""

# Check if test file exists
if [ ! -f "test.usdz" ]; then
    echo "❌ test.usdz not found"
    echo "Please place a USDZ file named 'test.usdz' in this directory"
    exit 1
fi

echo "✅ Found test.usdz"
echo ""

# Create output directory
mkdir -p test-output

# Step 1: Extract USDZ (it's a ZIP file)
echo "📦 Step 1: Extracting USDZ..."
unzip -q -o test.usdz -d test-output/extracted
echo "✅ Extracted"
echo ""

# Step 2: Find the main USD file
echo "📝 Step 2: Finding main USD file..."
MAIN_USD=$(find test-output/extracted -name "*.usda" -o -name "*.usdc" | head -1)

if [ -z "$MAIN_USD" ]; then
    echo "❌ No USD file found in USDZ"
    exit 1
fi

echo "✅ Found: $MAIN_USD"
echo ""

# Step 3: Check if we have usd2gltf or need to install it
echo "🔍 Step 3: Checking for USD to glTF converter..."

if command -v usd2gltf &> /dev/null; then
    echo "✅ usd2gltf found"
    echo ""
    echo "🔄 Converting USD to GLB..."
    usd2gltf -i "$MAIN_USD" -o test-output/test.glb
    
    if [ -f "test-output/test.glb" ]; then
        echo ""
        echo "✅✅✅ SUCCESS! ✅✅✅"
        echo ""
        echo "GLB file created: test-output/test.glb"
        ls -lh test-output/test.glb
    else
        echo "❌ Conversion failed"
    fi
else
    echo "❌ usd2gltf not found"
    echo ""
    echo "📦 Installing USD to glTF converter..."
    echo ""
    echo "Option 1: Install via pip (Python)"
    echo "  pip3 install usd2gltf"
    echo ""
    echo "Option 2: Use online converter"
    echo "  Upload to: https://products.aspose.app/3d/conversion/usdz-to-glb"
    echo ""
    echo "Option 3: Use Blender (most reliable)"
    echo "  1. Install Blender: brew install --cask blender"
    echo "  2. Open Blender"
    echo "  3. File → Import → Universal Scene Description (.usd/.usdc/.usda)"
    echo "  4. Select: $MAIN_USD"
    echo "  5. File → Export → glTF 2.0 (.glb/.gltf)"
    echo ""
    echo "Would you like me to try installing usd2gltf? (requires Python)"
    echo "Run: pip3 install usd-core pygltflib"
fi
