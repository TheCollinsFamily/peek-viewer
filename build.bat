@echo off
echo === Building Peek ===
echo.

pip install pyinstaller --quiet 2>nul

echo Running PyInstaller...
pyinstaller --onefile --windowed --name Peek --clean ^
    --add-data "peek;peek" ^
    main.py

echo.
if exist "dist\Peek.exe" (
    echo Build successful!
    echo Output: dist\Peek.exe
    echo.
    echo To distribute, share dist\Peek.exe
    echo Users can run register_peek.py to set it as default viewer.
) else (
    echo Build failed. Check errors above.
)
pause
