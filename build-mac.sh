#!/bin/bash
# ============================================================
# Peek / RFab Viewer - macOS Build Script
# ============================================================
# Builds a signed & notarized macOS .app bundle, then creates
# a distribution-ready ZIP and DMG.
#
# PREREQUISITES:
#   1. Python 3.10+ installed (python3 --version)
#   2. pip packages: pyinstaller, PySide6, Pillow
#   3. For code signing + notarization (optional but recommended):
#      - rfab-signing.key
#      - developerID_application.cer
#
# USAGE:
#   bash build-mac.sh
#
# Without signing credentials, it builds an unsigned .app
# (users will need to right-click > Open on first launch).
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "=========================================="
echo "  RFab Viewer - macOS Builder"
echo "=========================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ── Step 1: Prerequisites ──────────────────────────────────
echo -e "${YELLOW}Step 1/7: Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: python3 not found!${NC}"
    echo "Install from https://www.python.org/downloads/ or: brew install python"
    exit 1
fi
echo "  ✓ Python $(python3 --version 2>&1 | awk '{print $2}')"

if ! python3 -c "import PySide6" 2>/dev/null; then
    echo "  ⚙ Installing dependencies..."
    pip3 install -r requirements.txt
fi
echo "  ✓ PySide6 found"

if ! command -v pyinstaller &> /dev/null; then
    echo "  ⚙ Installing PyInstaller..."
    pip3 install pyinstaller
fi
echo "  ✓ PyInstaller $(pyinstaller --version 2>&1)"

# Check for signing credentials (optional)
HAS_SIGNING=false
if [ -f "rfab-signing.key" ] && [ -f "developerID_application.cer" ]; then
    HAS_SIGNING=true
    echo "  ✓ Signing credentials found"
else
    echo -e "  ${YELLOW}⚠ No signing credentials (rfab-signing.key + developerID_application.cer)${NC}"
    echo "    Building unsigned. Users will need to right-click > Open on first launch."
fi

# ── Step 2: Icon ───────────────────────────────────────────
echo ""
echo -e "${YELLOW}Step 2/7: Preparing app icon...${NC}"

if [ -f "peek.icns" ]; then
    echo -e "${GREEN}  ✓ peek.icns already exists${NC}"
else
    # Prefer high-res PNG source, fall back to .ico
    ICON_SOURCE=""
    if [ -f "peek.png" ]; then
        ICON_SOURCE="peek.png"
        echo "  ⚙ Generating peek.icns from peek.png..."
    elif [ -f "peek.ico" ]; then
        ICON_SOURCE="peek.ico"
        echo -e "  ${YELLOW}⚠ Using peek.ico (may be low-res). For best results, provide a 1024x1024 peek.png${NC}"
        echo "  ⚙ Generating peek.icns from peek.ico..."
    else
        echo -e "${RED}  ERROR: No peek.png, peek.ico, or peek.icns found!${NC}"
        exit 1
    fi

    # Generate .iconset from source using Pillow + sips
    python3 -c "
from PIL import Image
import subprocess, os

img = Image.open('$ICON_SOURCE')
# For .ico files, get the largest frame
if hasattr(img, 'n_frames') and img.n_frames > 1:
    best_size = 0
    best_frame = 0
    for i in range(img.n_frames):
        img.seek(i)
        if img.size[0] > best_size:
            best_size = img.size[0]
            best_frame = i
    img.seek(best_frame)

# Convert to RGBA and save as high-res PNG
img = img.convert('RGBA')
# Resize to 1024 if needed (LANCZOS for quality)
if img.size[0] < 1024:
    img = img.resize((1024, 1024), Image.LANCZOS)
img.save('/tmp/peek_icon_1024.png', format='PNG')
print(f'  Source: {img.size[0]}x{img.size[1]}')
img.close()

# Generate iconset
os.makedirs('peek.iconset', exist_ok=True)
for size, name in [
    (16, 'icon_16x16.png'), (32, 'icon_16x16@2x.png'),
    (32, 'icon_32x32.png'), (64, 'icon_32x32@2x.png'),
    (128, 'icon_128x128.png'), (256, 'icon_128x128@2x.png'),
    (256, 'icon_256x256.png'), (512, 'icon_256x256@2x.png'),
    (512, 'icon_512x512.png'), (1024, 'icon_512x512@2x.png'),
]:
    subprocess.run(['sips', '-z', str(size), str(size), '/tmp/peek_icon_1024.png',
                    '--out', f'peek.iconset/{name}'], capture_output=True)
" 2>/dev/null
    iconutil -c icns peek.iconset 2>/dev/null && rm -rf peek.iconset
    if [ -f "peek.icns" ]; then
        echo -e "${GREEN}  ✓ peek.icns generated${NC}"
    else
        echo -e "${RED}  ERROR: Failed to generate .icns. Please provide peek.icns manually.${NC}"
        echo "  Convert at: https://cloudconvert.com/png-to-icns"
        exit 1
    fi
fi

# ── Step 3: Certificate (if signing) ─────────────────────
echo ""
if [ "$HAS_SIGNING" = true ]; then
    echo -e "${YELLOW}Step 3/7: Installing certificate into Keychain...${NC}"

    openssl x509 -inform DER -in developerID_application.cer -out /tmp/peek-cert.pem 2>/dev/null || \
    openssl x509 -inform PEM -in developerID_application.cer -out /tmp/peek-cert.pem 2>/dev/null

    openssl pkcs12 -export -legacy -out /tmp/peek-signing.p12 \
        -inkey rfab-signing.key \
        -in /tmp/peek-cert.pem \
        -name "Developer ID Application: Pragmatist Foundation (AFBVMK56D7)" \
        -passout pass:peek 2>/dev/null

    security import /tmp/peek-signing.p12 -k ~/Library/Keychains/login.keychain-db -P "peek" -T /usr/bin/codesign 2>/dev/null || true
    rm -f /tmp/peek-cert.pem /tmp/peek-signing.p12

    CODESIGN_ID=$(
      security find-identity -v -p codesigning \
        | grep "Developer ID Application" \
        | head -1 \
        | sed 's/.*"\(Developer ID Application: .*\)"/\1/'
    )
    if [ -z "$CODESIGN_ID" ]; then
        echo -e "${YELLOW}  ⚠ Certificate not found in Keychain. Building unsigned.${NC}"
        HAS_SIGNING=false
    else
        echo -e "${GREEN}  ✓ Certificate: $CODESIGN_ID${NC}"
    fi
else
    echo -e "${YELLOW}Step 3/7: Skipping certificate (no credentials)${NC}"
fi

# ── Step 4: Clean previous build ─────────────────────────
echo ""
echo -e "${YELLOW}Step 4/7: Cleaning previous build...${NC}"
rm -rf build dist
echo -e "${GREEN}  ✓ Clean${NC}"

# ── Step 5: Build with PyInstaller ────────────────────────
echo ""
echo -e "${YELLOW}Step 5/7: Building app bundle with PyInstaller...${NC}"
pyinstaller Peek-mac.spec --noconfirm
echo -e "${GREEN}  ✓ App bundle created${NC}"

# ── Step 6: Code sign + Notarize ─────────────────────────
echo ""
if [ "$HAS_SIGNING" = true ]; then
    echo -e "${YELLOW}Step 6/7: Signing and notarizing...${NC}"

    APP_PATH="dist/RFab Viewer.app"

    # Deep-sign all binaries in the bundle
    codesign --deep --force --options runtime \
        --entitlements entitlements.plist \
        --sign "$CODESIGN_ID" \
        "$APP_PATH"
    echo "  ✓ Code signed"

    # Create ZIP for notarization submission
    ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "/tmp/peek-notarize.zip"

    # Submit for notarization
    APPLE_ID="collinsmalcolm@gmail.com"
    APPLE_TEAM_ID="AFBVMK56D7"
    # NOTE: Replace with your actual app-specific password or set as env var
    APPLE_PASSWORD="${APPLE_APP_SPECIFIC_PASSWORD:-zuvy-pvnw-ygmu-vydf}"

    if [ -n "$APPLE_PASSWORD" ]; then
        echo "  ⚙ Submitting to Apple for notarization (this takes 2-15 min)..."
        xcrun notarytool submit /tmp/peek-notarize.zip \
            --apple-id "$APPLE_ID" \
            --password "$APPLE_PASSWORD" \
            --team-id "$APPLE_TEAM_ID" \
            --wait

        # Staple the notarization ticket
        xcrun stapler staple "$APP_PATH"
        echo -e "${GREEN}  ✓ Notarization complete + stapled${NC}"
    else
        echo -e "${YELLOW}  ⚠ APPLE_APP_SPECIFIC_PASSWORD not set — skipping notarization${NC}"
        echo "    Set it to notarize:  export APPLE_APP_SPECIFIC_PASSWORD='xxxx-xxxx-xxxx-xxxx'"
    fi

    rm -f /tmp/peek-notarize.zip
else
    echo -e "${YELLOW}Step 6/7: Skipping signing (no credentials)${NC}"
fi

# ── Step 7: Create distribution archive ──────────────────
echo ""
echo -e "${YELLOW}Step 7/7: Creating distribution archive...${NC}"

APP_PATH="dist/RFab Viewer.app"
if [ -d "$APP_PATH" ]; then
    # Create ZIP (preserves code signature)
    ZIP_PATH="dist/RFab Viewer.zip"
    ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
    echo -e "${GREEN}  ✓ ZIP: $ZIP_PATH$(ls -lh "$ZIP_PATH" | awk '{print " ("$5")"}')"

    # Create DMG
    if command -v hdiutil &> /dev/null; then
        DMG_PATH="dist/RFab Viewer.dmg"
        hdiutil create -volname "RFab Viewer" \
            -srcfolder "$APP_PATH" \
            -ov -format UDZO \
            "$DMG_PATH" 2>/dev/null
        if [ -f "$DMG_PATH" ]; then
            # Sign the DMG too
            if [ "$HAS_SIGNING" = true ]; then
                codesign --sign "$CODESIGN_ID" "$DMG_PATH" 2>/dev/null || true
            fi
            echo -e "${GREEN}  ✓ DMG: $DMG_PATH$(ls -lh "$DMG_PATH" | awk '{print " ("$5")"}')"
        fi
    fi
else
    echo -e "${RED}  ERROR: App bundle not found at $APP_PATH${NC}"
    exit 1
fi

# ── Done ───────────────────────────────────────────────────
echo ""
echo "=========================================="
echo -e "${GREEN}  BUILD COMPLETE! ✓${NC}"
echo "=========================================="
echo ""
echo -e "${CYAN}Distribution files:${NC}"
ls -lh dist/*.zip dist/*.dmg 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
echo ""
echo -e "${CYAN}To install:${NC}"
echo "  1. Drag 'RFab Viewer.app' to /Applications"
echo "  2. Double-click to launch"
if [ "$HAS_SIGNING" != true ]; then
    echo ""
    echo -e "${YELLOW}  ⚠ App is unsigned. On first launch:${NC}"
    echo "    Right-click > Open > click 'Open' in the dialog"
    echo "    Or run: xattr -cr '/Applications/RFab Viewer.app'"
fi
echo ""
echo -e "${YELLOW}⚠ Always share the ZIP file, not the raw .app folder.${NC}"
echo ""
