# macOS Build Instructions — RFab Viewer (Peek)

## Quick Start (Unsigned Build)

On a Mac, open Terminal and run:

```bash
cd /path/to/peek-viewer
pip3 install -r requirements.txt
pip3 install pyinstaller
bash build-mac.sh
```

Output: `dist/RFab Viewer.app` + `dist/RFab Viewer.zip`

## Prerequisites

- **macOS 12+** (Monterey or later recommended)
- **Python 3.10+** — `brew install python` or https://www.python.org/downloads/
- **Xcode Command Line Tools** — `xcode-select --install`

## Signed + Notarized Build (Recommended for Distribution)

### One-Time Setup

You need 3 files in the peek-viewer folder (same creds as rf-bridge):

1. **`rfab-signing.key`** — Your Apple Developer private key
2. **`developerID_application.cer`** — Developer ID Application certificate

These are the SAME files used for rf-bridge builds. Copy them over.

### Build Command

```bash
export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
bash build-mac.sh
```

The script will:
1. Generate `peek.icns` from `peek.ico` (if not already present)
2. Import the certificate into your Keychain
3. Build the `.app` bundle via PyInstaller
4. Code sign with hardened runtime + entitlements
5. Submit to Apple for notarization (2-15 min wait)
6. Staple the notarization ticket
7. Create `.zip` and `.dmg` distribution files

### Credentials Reference (from rf-bridge)

| Item | Value |
|------|-------|
| Apple ID | collinsmalcolm@gmail.com |
| Team ID | AFBVMK56D7 |
| Team Name | Pragmatist Foundation |
| App-Specific Password | (generate at appleid.apple.com if expired) |

## Distribution

Always share the **ZIP** file, not the raw `.app` folder. Copying `.app` via AirDrop/Finder can corrupt the code signature.

## Installation (for recipients)

1. Download and unzip `RFab Viewer.zip`
2. Drag `RFab Viewer.app` into `/Applications`
3. Double-click to launch

If unsigned and macOS blocks it:
```bash
xattr -cr "/Applications/RFab Viewer.app"
```
Or: Right-click > Open > click "Open" in the security dialog.

## Setting as Default Viewer

On macOS there's no registry — instead:
1. Right-click any image/video file
2. Click "Get Info" (or Cmd+I)
3. Under "Open with", select "RFab Viewer"
4. Click "Change All..." to make it default for all files of that type

## Architecture Notes

| Feature | macOS Status |
|---------|-------------|
| Image viewing (Pillow + Qt) | ✅ Works |
| Video playback (QMediaPlayer) | ✅ Uses AVFoundation |
| .mp4, .mov | ✅ Native AVFoundation |
| .webm, .mkv | ⚠️ May need VLC/FFmpeg codecs |
| Boss key (Ctrl+`) | ✅ Works (Ctrl key, not Cmd) |
| System tray | ✅ Works (menu bar icon) |
| Single-instance IPC | ✅ TCP socket, cross-platform |
| Drag & drop | ✅ Works |
| File association ("Open With") | ✅ Via Info.plist CFBundleDocumentTypes |

## Troubleshooting

### "App is damaged and can't be opened"
```bash
xattr -cr "/Applications/RFab Viewer.app"
```

### Video doesn't play (MKV/WebM)
These formats require codec support beyond AVFoundation. Options:
- Convert to .mp4 before viewing
- Install VLC (its codecs may be picked up by Qt)

### PyInstaller: "No module named PySide6"
```bash
pip3 install PySide6 Pillow
```

### Icon missing or generic
Ensure `peek.icns` exists before building. The script auto-generates it from `peek.ico` using Pillow + `iconutil`.

### Build fails with "codesign" errors
If certificate import fails:
1. Double-click `developerID_application.cer` in Finder to import manually
2. Open Keychain Access > login > My Certificates — verify "Developer ID Application" appears
3. Re-run `bash build-mac.sh`

## File Structure (macOS additions)

```
peek-viewer/
├── Peek-mac.spec          ← PyInstaller spec for macOS .app bundle
├── build-mac.sh           ← Build script (all-in-one)
├── entitlements.plist     ← macOS hardened runtime entitlements
├── peek.icns              ← macOS icon (auto-generated from peek.ico)
├── MAC_BUILD_INSTRUCTIONS.md  ← This file
└── ...existing files...
```
