# hermes.ps1 - Hermes Web UI Control Script
# Usage: .\hermes.ps1 <command>
# Commands: start, stop, restart, status, open, close, browser

param(
    [Parameter(Position=0)]
    [ValidateSet("start","stop","restart","status","open","close","browser")]
    [string]$Command = "browser"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$PORT = 8648
$URL = "http://localhost:$PORT"

function Invoke-Hermes {
    param([string]$HermesArgs)
    Ensure-WSL
    # Write temp bash script to avoid PowerShell/bash quoting conflicts
    $tmpFile = [System.IO.Path]::GetTempFileName() + ".sh"
    $lines = @(
        '#!/bin/bash',
        'export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:/usr/local/bin:$PATH"',
        'HERMES_BIN=$(which hermes-web-ui 2>/dev/null)',
        'if [ -z "$HERMES_BIN" ]; then echo "ERROR: hermes-web-ui not found. Install it first: npm install -g hermes-web-ui"; exit 1; fi',
        "hermes-web-ui $HermesArgs"
    )
    [System.IO.File]::WriteAllText($tmpFile, ($lines -join "`n"))
    # Convert Windows path to WSL path
    $wslPath = wsl -- wslpath -a ($tmpFile -replace '\\','/')
    try {
        wsl -- bash $wslPath
    } finally {
        Remove-Item $tmpFile -ErrorAction SilentlyContinue
    }
}

function Get-DefaultWSLDistro {
    # Get the default WSL distribution name
    $list = wsl -l -v 2>$null
    $default = ($list | Select-String "\*" | ForEach-Object { ($_ -split '\s+')[1] })
    if ($default) { return $default }
    # Fallback: first distro listed
    foreach ($line in $list) {
        $name = ($line -split '\s+')[0] -replace '[^\w-]', ''
        if ($name -and $name -ne "NAME") { return $name }
    }
    return "Ubuntu"
}

function Ensure-WSL {
    $distro = Get-DefaultWSLDistro
    $wslStatus = wsl -l -v 2>$null
    if ($wslStatus -match "$distro\s+Stopped") {
        Write-Host "Starting WSL ($distro)..." -ForegroundColor Yellow
        wsl -d $distro -- echo "WSL ready" 2>$null
    }
}

function Open-Browser {
    # Check if already open in any browser
    $existing = Get-Process -Name "msedge","chrome","firefox","brave" -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle -match "localhost:$PORT|hermes" }

    if ($existing) {
        Write-Host "Browser already has hermes open. Focusing window..." -ForegroundColor Cyan
        # Bring existing window to front
        Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            public class Win32 {
                [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
                [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
            }
"@
        foreach ($proc in $existing) {
            if ($proc.MainWindowHandle -ne [IntPtr]::Zero) {
                [Win32]::ShowWindow($proc.MainWindowHandle, 9)  # SW_RESTORE
                [Win32]::SetForegroundWindow($proc.MainWindowHandle)
            }
        }
    } else {
        Write-Host "Opening browser at $URL" -ForegroundColor Green
        Start-Process $URL
    }
}

function Close-Browser {
    $closed = $false
    foreach ($browserName in @("msedge","chrome","firefox","brave")) {
        $procs = Get-Process -Name $browserName -ErrorAction SilentlyContinue
        foreach ($proc in $procs) {
            # Check if this process has a tab pointing to our URL
            if ($proc.MainWindowTitle -match "localhost:$PORT|hermes") {
                Write-Host "Closing hermes tab in $($proc.ProcessName)..." -ForegroundColor Yellow
                $proc.CloseMainWindow() | Out-Null
                $closed = $true
            }
        }
    }
    if (-not $closed) {
        Write-Host "No browser window found with hermes open." -ForegroundColor DarkYellow
    }
}

function Start-Hermes {
    Write-Host "Starting hermes-web-ui..." -ForegroundColor Green
    $result = Invoke-Hermes "start --port $PORT"
    Write-Host $result

    # Wait for the server to be ready
    $maxWait = 10
    $waited = 0
    while ($waited -lt $maxWait) {
        try {
            $response = Invoke-WebRequest -Uri $URL -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "Hermes Web UI is running at $URL" -ForegroundColor Green
                Open-Browser
                return
            }
        } catch { }
        Start-Sleep -Seconds 1
        $waited++
    }
    Write-Host "Server started. Opening browser..." -ForegroundColor Cyan
    Open-Browser
}

function Stop-Hermes {
    Write-Host "Stopping hermes-web-ui..." -ForegroundColor Yellow
    $result = Invoke-Hermes "stop"
    Write-Host $result
    Close-Browser
    Write-Host "Shutting down WSL..." -ForegroundColor Yellow
    wsl --shutdown 2>$null
    Write-Host "Hermes Web UI stopped. WSL shutdown." -ForegroundColor Red
}

function Restart-Hermes {
    Write-Host "Restarting hermes-web-ui..." -ForegroundColor Yellow
    $result = Invoke-Hermes "restart --port $PORT"
    Write-Host $result
    Open-Browser
}

function Get-Status {
    $result = Invoke-Hermes "status"
    Write-Host $result

    # Also check if port is accessible
    try {
        $response = Invoke-WebRequest -Uri $URL -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-Host "Web UI accessible at $URL (HTTP $($response.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Host "Web UI not accessible at $URL" -ForegroundColor Red
    }
}

# Main dispatch
switch ($Command) {
    "start"   { Start-Hermes }
    "stop"    { Stop-Hermes }
    "restart" { Restart-Hermes }
    "status"  { Get-Status }
    "open"    { Open-Browser }
    "close"   { Close-Browser }
    "browser" { Open-Browser }
}
