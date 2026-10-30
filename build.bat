@echo off
setlocal
cd /d "%~dp0"
echo === Building RFab Viewer ===
echo.

REM The exe that Windows opens for images and videos is dist\RFab Viewer.exe
REM (FIXES_2026-09-29.md, "Which program this is"). This script is the whole LOCAL build:
REM there is no committed .spec (*.spec is git-ignored), PyInstaller writes one per run.
REM It is not the release: the exe rfab.ai hands out is built, signed and uploaded by
REM rf-bridge's .github/workflows/build-viewer-win.yml (README.md, "Releases").
REM   --icon            the exe's own icon (Explorer, taskbar fallback)
REM   --add-data peek.ico;.   the window icon: peek/main.py _app_icon() loads it from the
REM                     bundle. Without it every window had no icon and the taskbar showed
REM                     the generic one (Oct 30 2026).
REM   --add-data peek;peek    the source files ride along as data; they let a later session
REM                     diff what a running exe was built from (%TEMP%\_MEI*\peek).

python -m pip install pyinstaller --quiet 2>nul

if exist dist-new rmdir /s /q dist-new
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "RFab Viewer" ^
    --distpath dist-new ^
    --icon peek.ico ^
    --add-data "peek.ico;." ^
    --add-data "peek;peek" ^
    main.py
if errorlevel 1 (
    echo Build failed. Check errors above.
    exit /b 1
)

if not exist "dist-new\RFab Viewer.exe" (
    echo Build failed: dist-new\RFab Viewer.exe missing.
    exit /b 1
)

REM A running "RFab Viewer.exe" cannot be overwritten, but it can be renamed: the running
REM copy keeps working from the .prev name and the next launch runs the new build.
if not exist dist mkdir dist
if exist "dist\RFab Viewer.exe" (
    del "dist\RFab Viewer.prev.exe" 2>nul
    if exist "dist\RFab Viewer.prev.exe" ren "dist\RFab Viewer.prev.exe" "RFab Viewer.prev.%RANDOM%.exe"
    ren "dist\RFab Viewer.exe" "RFab Viewer.prev.exe"
)
move /y "dist-new\RFab Viewer.exe" "dist\RFab Viewer.exe" >nul
rmdir /s /q dist-new 2>nul

echo.
echo Build successful: %~dp0dist\RFab Viewer.exe
echo (previous build kept as dist\RFab Viewer.prev.exe; close any open viewer so the next
echo  open runs the new one - a running old instance receives files from new launches.)
