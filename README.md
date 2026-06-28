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
