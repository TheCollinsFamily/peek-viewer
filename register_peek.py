"""
Register Peek as the default viewer for image and video files on Windows.

Run this once after installing or building Peek.
  - If Peek.exe exists in dist/, it registers that.
  - Otherwise it registers via python + main.py.

No admin rights required — writes to current user registry only.
"""

import sys
import os
import winreg
from pathlib import Path

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"]
VIDEO_EXTENSIONS = [".mp4", ".webm", ".avi", ".mkv", ".mov"]
ALL_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

APP_NAME = "PeekViewer"


def find_peek_command():
    """Find the best way to launch Peek."""
    script_dir = Path(__file__).resolve().parent

    # Prefer built exe
    exe_path = script_dir / "dist" / "Peek.exe"
    if exe_path.exists():
        return f'"{exe_path}" "%1"'

    # Fall back to python + main.py
    main_py = script_dir / "main.py"
    python = sys.executable
    if main_py.exists():
        return f'"{python}" "{main_py}" "%1"'

    return None


def register(command):
    """Register Peek in Windows registry for current user."""
    classes = winreg.HKEY_CURRENT_USER

    # Create app registration
    app_key_path = f"Software\\Classes\\{APP_NAME}"

    # Shell open command
    with winreg.CreateKey(classes, f"{app_key_path}\\shell\\open\\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)

    # Friendly name
    with winreg.CreateKey(classes, app_key_path) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Peek Media Viewer")

    # Register for each extension
    registered = []
    for ext in ALL_EXTENSIONS:
        ext_key_path = f"Software\\Classes\\{ext}\\OpenWithProgids"
        with winreg.CreateKey(classes, ext_key_path) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, "")
        registered.append(ext)

    return registered


def set_as_default(ext):
    """Set Peek as the default handler for a specific extension."""
    classes = winreg.HKEY_CURRENT_USER
    choice_path = f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\{ext}\\UserChoice"

    # UserChoice is protected — we can't write it directly.
    # But registering in OpenWithProgids makes Peek appear in "Open With" list.
    # Setting the extension's default value makes it the handler.
    try:
        with winreg.CreateKey(classes, f"Software\\Classes\\{ext}") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, APP_NAME)
        return True
    except OSError:
        return False


def main():
    if sys.platform != "win32":
        print("This script is for Windows only.")
        print("On macOS: Right-click a file > Get Info > Open with > select Peek > Change All")
        sys.exit(1)

    command = find_peek_command()
    if not command:
        print("Error: Could not find Peek.exe or main.py")
        sys.exit(1)

    print(f"Peek command: {command}")
    print()

    # Register in Open With list
    registered = register(command)
    print(f"Registered Peek in 'Open With' for {len(registered)} file types:")
    print(f"  Images: {', '.join(IMAGE_EXTENSIONS)}")
    print(f"  Videos: {', '.join(VIDEO_EXTENSIONS)}")
    print()

    # Ask if user wants to set as default
    response = input("Set Peek as the DEFAULT viewer for all these types? [y/N] ").strip().lower()
    if response == "y":
        success = 0
        for ext in ALL_EXTENSIONS:
            if set_as_default(ext):
                success += 1
        print(f"Set as default for {success}/{len(ALL_EXTENSIONS)} types.")
        print("Note: Some types may need a restart or manual 'Open With' selection.")
    else:
        print("Skipped. Peek will appear in the 'Open With' menu for these files.")

    print()
    print("Done! You can now right-click any image/video and find Peek in 'Open With'.")
    input("Press Enter to close...")


if __name__ == "__main__":
    main()
