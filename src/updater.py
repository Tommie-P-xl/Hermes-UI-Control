"""Auto-update via GitHub Releases."""
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from config import APP_VERSION, UPDATE_CHECK_URL


def parse_version(v: str) -> tuple:
    """Parse 'v1.2.3' or '1.2.3' into comparable tuple."""
    v = v.lstrip("v")
    parts = v.split(".")
    return tuple(int(p) for p in parts[:3])


def check_for_update() -> dict | None:
    """Check GitHub for a newer release. Returns release info dict or None."""
    try:
        req = urllib.request.Request(UPDATE_CHECK_URL, headers={"User-Agent": "HermesUIControl"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        remote_tag = data.get("tag_name", "")
        remote_ver = parse_version(remote_tag)
        local_ver = parse_version(APP_VERSION)

        if remote_ver > local_ver:
            # Find the exe asset
            asset_url = None
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".exe"):
                    asset_url = asset.get("browser_download_url")
                    break
            return {
                "version": remote_tag,
                "url": asset_url,
                "body": data.get("body", ""),
            }
    except Exception:
        pass
    return None


def perform_update(download_url: str) -> bool:
    """Download new version and replace current exe via a batch script."""
    if not getattr(sys, "frozen", False):
        return False  # Can only self-update packaged exe

    current_exe = Path(sys.executable)
    backup_exe = current_exe.with_suffix(".exe.bak")
    temp_dir = tempfile.mkdtemp()
    new_exe = Path(temp_dir) / "HermesUIControl_new.exe"

    try:
        # Download
        req = urllib.request.Request(download_url, headers={"User-Agent": "HermesUIControl"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(new_exe, "wb") as f:
                f.write(resp.read())

        # Write batch script to replace after exit
        bat_content = f"""@echo off
chcp 65001 >nul
echo Updating Hermes UI Control...
taskkill /F /PID {os.getpid()} >nul 2>&1
timeout /t 2 /nobreak >nul
move /Y "{current_exe}" "{backup_exe}" >nul 2>&1
move /Y "{new_exe}" "{current_exe}" >nul 2>&1
start "" "{current_exe}" --minimize
del /F "{backup_exe}" >nul 2>&1
rd /S /Q "{temp_dir}" >nul 2>&1
del /F "%~f0" >nul 2>&1
"""
        bat_path = Path(temp_dir) / "update.bat"
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        # Launch updater and exit
        subprocess.Popen(
            ["cmd", "/c", str(bat_path)],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )
        return True

    except Exception as e:
        # Cleanup on failure
        for p in [new_exe, backup_exe]:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        return False
