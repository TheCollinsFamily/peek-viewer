@echo off
echo === Packaging Peek for macOS build ===
echo.

set OUTPUT=peek-mac-source.zip
if exist "%OUTPUT%" del "%OUTPUT%"

REM Create zip with only what's needed
powershell -Command ^
  "Compress-Archive -Path @( ^
    'main.py', ^
    'requirements.txt', ^
    'peek.ico', ^
    'Peek-mac.spec', ^
    'build-mac.sh', ^
    'entitlements.plist', ^
    'MAC_BUILD_INSTRUCTIONS.md', ^
    'README.md', ^
    'peek' ^
  ) -DestinationPath '%OUTPUT%' -Force"

echo.
if exist "%OUTPUT%" (
    echo SUCCESS: %OUTPUT% created
    echo.
    echo Send this zip to your Mac user.
    echo They just need to:
    echo   1. Unzip
    echo   2. Open Terminal in the folder
    echo   3. Run: bash build-mac.sh
    echo.
    echo For SIGNED builds, also send them:
    echo   - rfab-signing.key
    echo   - developerID_application.cer
    echo   (from: C:\Users\Merry\.windsurf\Reality Fabricator\rf-bridge\)
) else (
    echo ERROR: Failed to create zip
)
echo.
pause
