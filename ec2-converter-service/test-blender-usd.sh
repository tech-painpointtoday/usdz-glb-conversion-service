#!/bin/bash

# Test if Blender has USD import support

echo "🧪 Testing Blender USD Support"
echo "================================"
echo ""

# Check Blender version
echo "📋 Blender version:"
blender --version | head -1
echo ""

# Test USD import capability
echo "🔍 Testing USD import..."

cat > /tmp/test_usd_import.py << 'EOF'
import bpy
import sys

try:
    # Try to access USD import operator
    if hasattr(bpy.ops.wm, 'usd_import'):
        print("✅ SUCCESS: USD import is available")
        sys.exit(0)
    else:
        print("❌ FAILED: USD import not found")
        print("Available importers:")
        for attr in dir(bpy.ops.wm):
            if 'import' in attr.lower():
                print(f"  - {attr}")
        sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
EOF

blender --background --python /tmp/test_usd_import.py 2>&1 | grep -E "(SUCCESS|FAILED|ERROR|Available|import)"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "✅ Blender has USD support!"
    echo "   The converter should work."
else
    echo ""
    echo "❌ Blender does NOT have USD support!"
    echo ""
    echo "📦 Solutions:"
    echo ""
    echo "Option 1: Install Blender from Snap (includes USD)"
    echo "  sudo snap install blender --classic"
    echo "  sudo ln -sf /snap/bin/blender /usr/local/bin/blender"
    echo ""
    echo "Option 2: Use alternative conversion method"
    echo "  We can use a Python USD library instead"
    echo ""
fi

rm /tmp/test_usd_import.py
