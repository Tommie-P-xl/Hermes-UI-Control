@echo off
chcp 65001 >nul
echo ============================================
echo   Hermes Web UI Control - Installer
echo ============================================
echo.

:: Check WSL is installed
wsl -l >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] WSL not installed. Please install WSL first:
    echo   wsl --install
    pause
    exit /b 1
)

:: Check hermes-web-ui is installed in WSL
echo Checking hermes-web-ui in WSL...
wsl -- bash -c "export PATH=\"$HOME/.npm-global/bin:$PATH\"; which hermes-web-ui" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] hermes-web-ui not found in WSL.
    echo Installing hermes-web-ui...
    wsl -- bash -c "npm install -g hermes-web-ui"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install. Make sure Node.js ^>= 23 is installed in WSL.
        pause
        exit /b 1
    )
)

echo.
echo [OK] hermes-web-ui is ready.
echo.

:: Add to PATH
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
powershell -Command "$p=[Environment]::GetEnvironmentVariable('Path','User'); if($p -notlike '*%SCRIPT_DIR%*'){[Environment]::SetEnvironmentVariable('Path','$p;%SCRIPT_DIR%','User'); Write-Host '[OK] Added to PATH'} else {Write-Host '[OK] Already in PATH'}"

:: Create desktop shortcuts
powershell -ExecutionPolicy Bypass -Command ^
  "$desktop=[Environment]::GetFolderPath('Desktop'); $shell=New-Object -ComObject WScript.Shell; " ^
  "@('Start|start|Start Hermes Web UI','Stop|stop|Stop Hermes Web UI and shutdown WSL','Browser|browser|Open Hermes Web UI in browser') | ForEach-Object { " ^
  "  $n,$a,$d=$_ -split '\|'; " ^
  "  $lnk=$shell.CreateShortcut(\"$desktop\Hermes - $n.lnk\"); " ^
  "  $lnk.TargetPath='powershell.exe'; " ^
  "  $lnk.Arguments='-ExecutionPolicy Bypass -WindowStyle Hidden -File %SCRIPT_DIR%\hermes.ps1 ' + $a; " ^
  "  $lnk.WorkingDirectory='%SCRIPT_DIR%'; " ^
  "  $lnk.IconLocation='powershell.exe,0'; " ^
  "  $lnk.Description=$d; " ^
  "  $lnk.Save(); " ^
  "  Write-Host \"[OK] Shortcut: Hermes - $n\" " ^
  "}"

echo.
echo ============================================
echo   Install complete!
echo ============================================
echo.
echo   Desktop shortcuts:
echo     Hermes - Start    Start + open browser
echo     Hermes - Stop     Stop + close WSL
echo     Hermes - Browser  Open browser only
echo.
echo   Or use commands in any terminal:
echo     hermes start / stop / browser / status
echo.
pause
