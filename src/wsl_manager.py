"""WSL and hermes-web-ui management — ported from hermes.ps1."""
import subprocess
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from config import HERMES_PORT, HERMES_URL
from main import log

# State tracking
_server_running = False
_status_lock = threading.Lock()


def _decode_output(data: bytes) -> str:
    """Decode subprocess output, trying multiple encodings."""
    if not data:
        return ""
    for enc in ("utf-8", "utf-16-le", "gbk", "gb2312", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return data.decode("utf-8", errors="replace")


def _run_cmd(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    """Run a command and return (returncode, combined output)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        stdout = _decode_output(result.stdout)
        stderr = _decode_output(result.stderr)
        return result.returncode, (stdout + stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "Command timed out"
    except FileNotFoundError:
        return -1, f"Command not found: {cmd[0]}"


def _run_wsl(bash_script: str, timeout: int = 30) -> tuple[int, str]:
    """Execute a bash command inside WSL via bash -l -c (login shell for PATH)."""
    full_script = (
        'export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:/usr/local/bin:$PATH" && '
        + bash_script
    )
    return _run_cmd(["wsl", "--", "bash", "-l", "-c", full_script], timeout=timeout)


def get_default_distro() -> str:
    """Get the default WSL distribution name."""
    rc, out = _run_cmd(["wsl", "-l", "-v"])
    if rc != 0:
        return "Ubuntu"
    for line in out.splitlines():
        if "*" in line:
            parts = line.split()
            for p in parts:
                cleaned = p.strip().replace("*", "")
                if cleaned and cleaned != "NAME":
                    return cleaned
    # Fallback: first non-header line
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] != "NAME":
            return parts[0].replace("*", "")
    return "Ubuntu"


def check_wsl() -> bool:
    """Check if WSL is installed and has a distro."""
    rc, out = _run_cmd(["wsl", "-l"])
    return rc == 0 and len(out.strip()) > 0


def check_hermes() -> bool:
    """Check if hermes-web-ui is installed in WSL (single combined call)."""
    script = (
        'command -v hermes-web-ui 2>/dev/null && exit 0; '
        'test -x "$HOME/.npm-global/bin/hermes-web-ui" && exit 0; '
        'npm list -g hermes-web-ui 2>/dev/null | grep -q hermes-web-ui && exit 0; '
        'exit 1'
    )
    rc, _ = _run_wsl(script, timeout=15)
    return rc == 0


def ensure_wsl():
    """Start WSL distro if it's stopped."""
    distro = get_default_distro()
    rc, out = _run_cmd(["wsl", "-l", "-v"])
    if f"{distro}" in out and "Stopped" in out:
        _run_cmd(["wsl", "-d", distro, "--", "echo", "ready"], timeout=15)


def is_port_open() -> bool:
    """Check if hermes-web-ui is responding on the port."""
    try:
        req = urllib.request.Request(HERMES_URL)
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def start() -> str:
    """Start hermes-web-ui and open browser."""
    global _server_running
    log("start() called, ensuring WSL...")
    ensure_wsl()

    script = f'hermes-web-ui start --port {HERMES_PORT}'
    log(f"start() running WSL command: {script}")
    rc, out = _run_wsl(script, timeout=30)
    log(f"start() WSL result: rc={rc}, out={out[:200] if out else '(empty)'}")

    # Poll for readiness
    for i in range(15):
        if is_port_open():
            _server_running = True
            log(f"start() port open after {i}s")
            return "Hermes Web UI started successfully."
        time.sleep(1)

    _server_running = True
    log("start() port not open after 15s")
    return "Hermes Web UI started (waiting for ready state)."


def stop() -> str:
    """Stop hermes-web-ui and shutdown WSL."""
    global _server_running
    log("stop() called")
    script = 'hermes-web-ui stop'
    rc, out = _run_wsl(script, timeout=15)
    log(f"stop() WSL result: rc={rc}, out={out[:200] if out else '(empty)'}")
    _server_running = False

    _run_cmd(["wsl", "--shutdown"], timeout=10)
    log("stop() WSL shutdown done")
    return "Hermes Web UI stopped. WSL shutdown."


def restart() -> str:
    """Restart hermes-web-ui."""
    ensure_wsl()
    script = f"""
HERMES_BIN=$(which hermes-web-ui 2>/dev/null)
if [ -z "$HERMES_BIN" ]; then echo "ERROR: hermes-web-ui not found"; exit 1; fi
hermes-web-ui restart --port {HERMES_PORT}
"""
    _run_wsl(script, timeout=30)

    for _ in range(15):
        if is_port_open():
            return "Hermes Web UI restarted."
        time.sleep(1)

    return "Hermes Web UI restart initiated."


def status() -> tuple[bool, str]:
    """Get hermes-web-ui status. Returns (running, description)."""
    script = """
HERMES_BIN=$(which hermes-web-ui 2>/dev/null)
if [ -n "$HERMES_BIN" ]; then hermes-web-ui status; else echo "NOT_INSTALLED"; fi
"""
    rc, out = _run_wsl(script, timeout=10)
    port_ok = is_port_open()

    if port_ok:
        return True, f"Running at {HERMES_URL}"
    elif "running" in out.lower():
        return True, "Service starting..."
    else:
        return False, "Not running"


def open_browser():
    """Open or focus the default browser to hermes URL."""
    import webbrowser
    import ctypes

    # Try to find and focus existing window first
    browsers = ["msedge", "chrome", "firefox", "brave"]
    found = False

    try:
        # Use PowerShell to find and focus browser window
        ps_script = f"""
$procs = Get-Process -Name {','.join(browsers)} -ErrorAction SilentlyContinue |
    Where-Object {{ $_.MainWindowTitle -match 'localhost:{HERMES_PORT}|hermes' }}
if ($procs) {{
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Focus {{
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}}
"@
    foreach ($p in $procs) {{
        if ($p.MainWindowHandle -ne [IntPtr]::Zero) {{
            [Win32Focus]::ShowWindow($p.MainWindowHandle, 9)
            [Win32Focus]::SetForegroundWindow($p.MainWindowHandle)
        }}
    }}
    Write-Output "FOCUSED"
}} else {{
    Write-Output "NOT_FOUND"
}}
"""
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        found = "FOCUSED" in result.stdout
    except Exception:
        pass

    if not found:
        webbrowser.open(HERMES_URL)


def get_status_icon_state() -> str:
    """Return 'running', 'stopped', or 'unknown' for tray icon state."""
    if is_port_open():
        return "running"
    return "stopped"
