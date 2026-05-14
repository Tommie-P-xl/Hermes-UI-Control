"""Windows native hermes-web-ui management."""
import subprocess
import threading
import time
import urllib.request
import webbrowser
import ctypes
from pathlib import Path

from config import HERMES_PORT, HERMES_URL
from main import log

# State tracking
_server_running = False
_status_lock = threading.Lock()
_hermes_process = None


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


def check_hermes() -> bool:
    """Check if hermes-web-ui is installed on Windows."""
    # Check via where command
    rc, out = _run_cmd(["where", "hermes-web-ui"])
    if rc == 0:
        return True

    # Check common npm global paths
    npm_paths = [
        Path.home() / "AppData" / "Roaming" / "npm" / "hermes-web-ui.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "hermes-web-ui.exe",
        Path("C:/Program Files/nodejs/hermes-web-ui.cmd"),
    ]
    for p in npm_paths:
        if p.exists():
            return True

    # Try npm list
    rc, out = _run_cmd(["npm", "list", "-g", "hermes-web-ui"])
    return rc == 0 and "hermes-web-ui" in out


def is_port_open() -> bool:
    """Check if hermes-web-ui is responding on the port."""
    try:
        req = urllib.request.Request(HERMES_URL)
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def start() -> str:
    """Start hermes-web-ui natively on Windows."""
    global _server_running, _hermes_process
    log("windows_manager.start() called")

    # Try to start hermes-web-ui
    cmd = f"hermes-web-ui start --port {HERMES_PORT}"
    log(f"start() running: {cmd}")

    try:
        # Use subprocess.Popen to start in background
        _hermes_process = subprocess.Popen(
            ["cmd", "/c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        log(f"start() process started with PID: {_hermes_process.pid}")
    except Exception as e:
        log(f"start() error starting process: {e}")
        return f"Failed to start: {e}"

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
    """Stop hermes-web-ui on Windows."""
    global _server_running, _hermes_process
    log("windows_manager.stop() called")

    # Try graceful stop first
    cmd = "hermes-web-ui stop"
    rc, out = _run_cmd(["cmd", "/c", cmd], timeout=10)
    log(f"stop() graceful stop result: rc={rc}, out={out[:200]}")

    # Kill process if still running
    if _hermes_process and _hermes_process.poll() is None:
        log("stop() terminating process...")
        try:
            _hermes_process.terminate()
            _hermes_process.wait(timeout=5)
        except Exception as e:
            log(f"stop() error terminating: {e}")
            try:
                _hermes_process.kill()
            except Exception:
                pass
        _hermes_process = None

    # Also kill any remaining hermes-web-ui processes
    _run_cmd(["taskkill", "/F", "/IM", "hermes-web-ui.exe"], timeout=5)
    _run_cmd(["taskkill", "/F", "/IM", "node.exe", "/FI", "WINDOWTITLE eq hermes*"], timeout=5)

    _server_running = False
    log("stop() done")
    return "Hermes Web UI stopped."


def restart() -> str:
    """Restart hermes-web-ui on Windows."""
    log("windows_manager.restart() called")

    # Stop first
    stop()
    time.sleep(1)

    # Then start
    return start()


def status() -> tuple[bool, str]:
    """Get hermes-web-ui status. Returns (running, description)."""
    port_ok = is_port_open()

    if port_ok:
        return True, f"Running at {HERMES_URL}"

    # Check if process is running
    rc, out = _run_cmd(["tasklist", "/FI", "IMAGENAME eq hermes-web-ui.exe"], timeout=5)
    if "hermes-web-ui.exe" in out:
        return True, "Process running but port not ready"

    return False, "Not running"


def open_browser():
    """Open the default browser to hermes URL. Always opens a new tab."""
    webbrowser.open_new_tab(HERMES_URL)


def get_status_icon_state() -> str:
    """Return 'running', 'stopped', or 'unknown' for tray icon state."""
    if is_port_open():
        return "running"
    return "stopped"
