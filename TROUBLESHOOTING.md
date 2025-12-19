# Troubleshooting: "The application can't be opened" on macOS

If you're still getting the error after trying the basic fixes, here are additional solutions:

## 🔍 Diagnostic Steps

### Step 1: Run Diagnostic Script

1. Open Terminal
2. Navigate to the folder with XeusGUI.app
3. Run the diagnostic script:
   ```bash
   ./diagnose_macos.sh
   ```

This will check:
- File permissions
- Quarantine attributes
- Architecture compatibility (arm64 vs x86_64)
- Code signature
- Missing libraries
- macOS version compatibility

### Step 2: Check Architecture Compatibility

**Problem:** The app might be built for a different CPU architecture.

**Check your Mac's architecture:**
```bash
uname -m
```
- `arm64` = Apple Silicon (M1/M2/M3)
- `x86_64` = Intel Mac

**Check app's architecture:**
```bash
file XeusGUI.app/Contents/MacOS/XeusGUI
```

**Solution:** If architectures don't match, you need to rebuild the app for your Mac's architecture.

### Step 3: Check for Missing Libraries

**Problem:** Required Qt libraries might be missing or incompatible.

**Check libraries:**
```bash
otool -L XeusGUI.app/Contents/MacOS/XeusGUI | grep -i "not found"
```

If you see "not found" entries, the app needs to be rebuilt with proper library paths.

### Step 4: Try Running from Terminal

**This will show the actual error message:**

```bash
./XeusGUI.app/Contents/MacOS/XeusGUI
```

Common errors:
- `dyld: Library not loaded` - Missing Qt libraries
- `Killed: 9` - Architecture mismatch or macOS version too old
- `Segmentation fault` - Corrupted installation

### Step 5: Check Console Logs

1. Open **Console.app** (Applications → Utilities)
2. Search for "XeusGUI"
3. Look for error messages

### Step 6: Check System Settings

1. Go to **System Settings** → **Privacy & Security**
2. Scroll down to **Security**
3. Look for any messages about XeusGUI
4. Click **"Allow Anyway"** if present

### Step 7: Disable Gatekeeper (Advanced)

**⚠️ Only do this if nothing else works:**

```bash
# Temporarily disable Gatekeeper (requires admin password)
sudo spctl --master-disable

# Try launching the app

# Re-enable Gatekeeper after testing
sudo spctl --master-enable
```

## 🛠️ Advanced Fixes

### Fix 1: Complete Re-signing

```bash
# Remove all signatures
codesign --remove-signature XeusGUI.app

# Re-sign with adhoc signature
codesign --force --deep --sign - XeusGUI.app

# Verify signature
codesign -dv --verbose=4 XeusGUI.app
```

### Fix 2: Fix All Permissions

```bash
# Fix executable permissions
chmod +x XeusGUI.app/Contents/MacOS/XeusGUI

# Fix directory permissions
chmod -R 755 XeusGUI.app

# Remove all extended attributes
xattr -cr XeusGUI.app
```

### Fix 3: Check Disk Space

```bash
df -h .
```

Make sure you have at least 1 GB free space.

### Fix 4: Move to Applications Folder

Sometimes macOS is more permissive with apps in the Applications folder:

```bash
# Move to Applications
mv XeusGUI.app /Applications/

# Try launching
open /Applications/XeusGUI.app
```

## 📋 Common Error Messages and Solutions

### "Killed: 9"
- **Cause:** Architecture mismatch or macOS version too old
- **Solution:** Rebuild for correct architecture or update macOS

### "dyld: Library not loaded"
- **Cause:** Missing Qt libraries
- **Solution:** Rebuild the app with proper library bundling

### "The application can't be opened"
- **Cause:** Gatekeeper blocking unsigned app
- **Solution:** Use right-click → Open, or disable Gatekeeper temporarily

### "Bad CPU type in executable"
- **Cause:** Architecture mismatch
- **Solution:** Rebuild for your Mac's architecture

## 🔄 Rebuilding the Application

If the app was built for the wrong architecture, you need to rebuild it:

### For Apple Silicon (M1/M2/M3):
```bash
# The app should be built with arm64 target
# Current build is for arm64
```

### For Intel Mac:
```bash
# You need to rebuild with x86_64 target
# This requires rebuilding on an Intel Mac or using cross-compilation
```

## 📞 Getting Help

If none of these solutions work:

1. Run the diagnostic script and save the output
2. Try running from terminal and save the error message
3. Check Console.app logs
4. Create an issue on GitHub with:
   - Your Mac model and macOS version
   - Output from diagnostic script
   - Error messages from terminal
   - Console.app logs

## 🔗 Related Files

- `fix_macos_permissions.sh` - Basic permission fix script
- `diagnose_macos.sh` - Comprehensive diagnostic script
- `HOW_TO_INSTALL.txt` - Basic installation instructions

