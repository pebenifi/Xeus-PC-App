#!/bin/bash
# Comprehensive diagnostic script for XeusGUI macOS launch issues
# This script checks all possible causes of launch failures

APP_PATH="XeusGUI.app"
EXECUTABLE_PATH="$APP_PATH/Contents/MacOS/XeusGUI"

echo "═══════════════════════════════════════════════════════════════"
echo "  XEUSGUI DIAGNOSTIC TOOL"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check 1: Application exists
echo "✓ Checking if application exists..."
if [ ! -d "$APP_PATH" ]; then
    echo "❌ ERROR: $APP_PATH not found!"
    echo "   Make sure you are in the correct directory."
    exit 1
fi
echo "   ✅ Application found"
echo ""

# Check 2: Executable exists
echo "✓ Checking if executable exists..."
if [ ! -f "$EXECUTABLE_PATH" ]; then
    echo "❌ ERROR: Executable not found at $EXECUTABLE_PATH"
    exit 1
fi
echo "   ✅ Executable found"
echo ""

# Check 3: File permissions
echo "✓ Checking file permissions..."
if [ ! -x "$EXECUTABLE_PATH" ]; then
    echo "⚠️  WARNING: Executable doesn't have execute permission"
    echo "   Fixing permissions..."
    chmod +x "$EXECUTABLE_PATH"
    echo "   ✅ Permissions fixed"
else
    echo "   ✅ Permissions OK"
fi
echo ""

# Check 4: Extended attributes (quarantine)
echo "✓ Checking extended attributes..."
QUARANTINE=$(xattr -l "$APP_PATH" 2>/dev/null | grep -i quarantine)
if [ -n "$QUARANTINE" ]; then
    echo "⚠️  WARNING: Quarantine attribute found"
    echo "   Removing quarantine..."
    xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null
    xattr -cr "$APP_PATH" 2>/dev/null
    echo "   ✅ Quarantine removed"
else
    echo "   ✅ No quarantine attribute"
fi
echo ""

# Check 5: Architecture compatibility
echo "✓ Checking architecture compatibility..."
ARCH=$(uname -m)
FILE_ARCH=$(file "$EXECUTABLE_PATH" | grep -oE "(arm64|x86_64)")
echo "   System architecture: $ARCH"
echo "   Application architecture: $FILE_ARCH"

if [ "$ARCH" = "arm64" ] && [ "$FILE_ARCH" != "arm64" ]; then
    echo "❌ ERROR: Architecture mismatch!"
    echo "   System is $ARCH but app is $FILE_ARCH"
    echo "   You need to rebuild the app for your architecture."
elif [ "$ARCH" = "x86_64" ] && [ "$FILE_ARCH" != "x86_64" ]; then
    echo "❌ ERROR: Architecture mismatch!"
    echo "   System is $ARCH but app is $FILE_ARCH"
    echo "   You need to rebuild the app for your architecture."
else
    echo "   ✅ Architecture compatible"
fi
echo ""

# Check 6: macOS version
echo "✓ Checking macOS version..."
MACOS_VERSION=$(sw_vers -productVersion)
echo "   macOS version: $MACOS_VERSION"
MAJOR_VERSION=$(echo $MACOS_VERSION | cut -d. -f1)
MINOR_VERSION=$(echo $MACOS_VERSION | cut -d. -f2)

if [ "$MAJOR_VERSION" -lt 10 ] || ([ "$MAJOR_VERSION" -eq 10 ] && [ "$MINOR_VERSION" -lt 13 ]); then
    echo "⚠️  WARNING: macOS version may be too old (requires 10.13+)"
else
    echo "   ✅ macOS version OK"
fi
echo ""

# Check 7: Code signature
echo "✓ Checking code signature..."
SIGNATURE=$(codesign -dv --verbose=4 "$APP_PATH" 2>&1)
if echo "$SIGNATURE" | grep -q "adhoc"; then
    echo "   ⚠️  Application has adhoc signature (unsigned)"
    echo "   Resigning application..."
    codesign --force --deep --sign - "$APP_PATH" 2>&1 | grep -v "^$APP_PATH:"
    echo "   ✅ Application resigned"
elif echo "$SIGNATURE" | grep -q "valid"; then
    echo "   ✅ Code signature valid"
else
    echo "   ⚠️  Code signature issue detected"
    echo "   Attempting to fix..."
    codesign --force --deep --sign - "$APP_PATH" 2>&1 | grep -v "^$APP_PATH:"
    echo "   ✅ Signature fixed"
fi
echo ""

# Check 8: Required libraries
echo "✓ Checking for required libraries..."
DYLIBS=$(otool -L "$EXECUTABLE_PATH" 2>/dev/null | head -5)
if [ -z "$DYLIBS" ]; then
    echo "   ⚠️  WARNING: Could not read library dependencies"
else
    echo "   ✅ Library dependencies readable"
    MISSING_LIBS=$(echo "$DYLIBS" | grep -i "not found")
    if [ -n "$MISSING_LIBS" ]; then
        echo "   ❌ ERROR: Missing required libraries!"
        echo "$MISSING_LIBS"
    else
        echo "   ✅ All required libraries found"
    fi
fi
echo ""

# Check 9: Try to run and capture error
echo "✓ Attempting to run application (this will show errors)..."
echo "   Running: $EXECUTABLE_PATH"
echo "   ───────────────────────────────────────────────────────"
"$EXECUTABLE_PATH" 2>&1 | head -20
EXIT_CODE=$?
echo "   ───────────────────────────────────────────────────────"
if [ $EXIT_CODE -eq 0 ]; then
    echo "   ✅ Application launched successfully!"
else
    echo "   ❌ Application failed with exit code: $EXIT_CODE"
fi
echo ""

# Final recommendations
echo "═══════════════════════════════════════════════════════════════"
echo "  RECOMMENDATIONS"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "If the application still doesn't launch:"
echo ""
echo "1. Try right-click → Open (instead of double-click)"
echo "2. Check System Settings → Privacy & Security → Allow"
echo "3. Run this command to see detailed errors:"
echo "   $EXECUTABLE_PATH"
echo ""
echo "4. Check Console.app for system logs:"
echo "   - Open Console.app"
echo "   - Search for 'XeusGUI'"
echo ""
echo "5. If architecture mismatch detected, rebuild the app:"
echo "   - For Intel Mac: rebuild with x86_64 target"
echo "   - For Apple Silicon: rebuild with arm64 target"
echo ""

