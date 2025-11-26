#!/bin/bash
# Script to fix macOS application launch issues
# This script removes quarantine attributes and fixes permissions for XeusGUI.app
# Usage: ./fix_macos_permissions.sh

APP_PATH="XeusGUI.app"

# Check if the application exists
if [ ! -d "$APP_PATH" ]; then
    echo "❌ Error: $APP_PATH not found!"
    echo "Make sure you are in the directory containing the application."
    exit 1
fi

echo "🔧 Fixing permissions for $APP_PATH..."

# Step 1: Remove quarantine attribute
# macOS adds this attribute to downloaded files, which blocks execution
echo "1. Removing quarantine attribute..."
xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || echo "   Quarantine not found or already removed"

# Step 2: Clear all extended attributes that might block execution
echo "2. Clearing extended attributes..."
xattr -cr "$APP_PATH" 2>/dev/null || echo "   Attributes cleared"

# Step 3: Set execute permissions on the executable
echo "3. Setting execute permissions..."
chmod +x "$APP_PATH/Contents/MacOS/XeusGUI" 2>/dev/null || echo "   Permissions already set"

# Step 4: Sign the application with adhoc signature
# This allows the app to run without a developer certificate
echo "4. Signing application..."
codesign --force --deep --sign - "$APP_PATH" 2>/dev/null || echo "   Signing completed or not required"

echo ""
echo "✅ Done! Now try to launch the application:"
echo "   - Double-click on $APP_PATH"
echo "   - Or via terminal: open $APP_PATH"
echo ""
echo "If macOS still blocks the launch:"
echo "1. Right-click on the application → 'Open'"
echo "2. Go to System Settings → Privacy & Security"
echo "3. Click 'Open Anyway' next to the warning"
