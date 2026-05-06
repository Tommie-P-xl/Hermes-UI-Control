@echo off
chcp 65001 >nul
echo ============================================
echo   Building Hermes UI Control
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+.
    pause
    exit /b 1
)

:: Install dependencies
echo Installing dependencies...
pip install pystray Pillow pyinstaller --quiet

echo.
echo Building executable...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name HermesUIControl ^
    --icon src\icon.ico ^
    --paths src ^
    --hidden-import pystray._win32 ^
    --hidden-import pystray._appindicator ^
    --hidden-import pystray._gtk ^
    --hidden-import PIL ^
    --noconfirm ^
    --clean ^
    src\main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build complete!
echo   Output: dist\HermesUIControl.exe
echo ============================================
echo.
pause
