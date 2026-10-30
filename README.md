# Peek — Lightweight Media Viewer

A minimal, chromeless desktop app for viewing images and looping videos. No toolbars, no clutter — just your content.

## Features

- **Borderless image viewer** — arrow keys to navigate, scroll to zoom
- **Auto-looping video player** — no controls, no OSD, just video
- **Grid/collage mode** — multiple files in equal-sized panels
- **Slideshow mode** — auto-advance with configurable timing
- **Folder auto-unzip** — extract all ZIPs in a folder with one click
- **Boss key** — Ctrl+` instantly hides everything

## Install

```bash
pip install -r requirements.txt
python main.py
```

## Releases (what rfab.ai/downloads hands out)

| Download | Built by | When |
|---|---|---|
| `RFab Viewer.dmg` (macOS, signed + notarized) | `.github/workflows/build.yml` here | every push to master |
| `RFab Viewer Linux.tar.gz` (x86-64; `linux/install.sh` adds the menu entry and Open With) | `.github/workflows/build.yml` here | every push to master |
| `RFab Viewer.exe` (Windows, Azure Trusted Signing) | `build-viewer-win.yml` in `TheCollinsFamily/rf-bridge`, which holds the signing secrets | when `.github/viewer-release.txt` there names a new commit of this repo and is pushed |

All three land in `s3://rfab-media/downloads/`, and `downloads/versions/<file>.json` beside each says
which commit it was built from. `build.bat` builds only the local `dist\RFab Viewer.exe` this PC opens
images with. Details and the Oct 30 2026 history: `FIXES_2026-10-30.md`.

## Supported Formats

- **Images:** PNG, JPG, JPEG, WebP, GIF, BMP, TIFF
- **Videos:** MP4, WebM, AVI, MKV, MOV

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Left/Right | Previous/Next file |
| Space | Pause/Resume video |
| F | Toggle fullscreen |
| G | Open grid mode with folder |
| S | Start slideshow |
| Esc | Close viewer / Exit fullscreen |
| Ctrl+` | Boss key — hide all windows |
| Double-click | Close viewer |
