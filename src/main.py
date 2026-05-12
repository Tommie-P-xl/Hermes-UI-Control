"""Hermes UI Control — main entry point."""
import ctypes
import sys
import threading
import time
from pathlib import Path
from datetime import datetime

# Set DPI awareness BEFORE any UI creation (fixes blurry menu text)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Simple file logger for debugging
LOG_FILE = Path.home() / ".hermes-ui-control" / "app.log"


def log(msg: str):
    """Write a timestamped log line."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

# Single instance mutex
_mutex_handle = None


def acquire_mutex() -> bool:
    """Try to acquire a named mutex. Returns False if already running."""
    global _mutex_handle
    mutex_name = "HermesUIControl_SingleInstance"
    _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def release_mutex():
    """Release the mutex."""
    global _mutex_handle
    if _mutex_handle:
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None


def check_environment() -> tuple[bool, str]:
    """Verify hermes-web-ui is available based on run mode."""
    import config as app_config

    run_mode = app_config.get("run_mode")

    if run_mode == "windows":
        import windows_manager
        if not windows_manager.check_hermes():
            return False, (
                "hermes-web-ui is not installed on Windows.\n"
                "Install it with: npm install -g hermes-web-ui"
            )
    else:
        import wsl_manager
        if not wsl_manager.check_wsl():
            return False, "WSL is not installed. Please install WSL first:\n  wsl --install"
        if not wsl_manager.check_hermes():
            return False, (
                "hermes-web-ui is not installed in WSL.\n"
                "Install it with: npm install -g hermes-web-ui"
            )

    return True, "OK"


def show_error(title: str, message: str):
    """Show a Windows message box for errors."""
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONERROR


def show_info(title: str, message: str):
    """Show a Windows message box for info."""
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)  # MB_ICONINFORMATION


def main():
    # Parse arguments
    args = sys.argv[1:]
    start_minimized = "--minimize" in args
    auto_start = "--start" in args

    log("App starting")

    # Single instance check
    if not acquire_mutex():
        log("Another instance already running")
        show_info(
            "Hermes UI Control",
            "Hermes UI Control is already running.\nCheck the system tray.",
        )
        sys.exit(0)

    try:
        # Check environment
        log("Checking environment...")
        ok, msg = check_environment()
        if not ok:
            log(f"Environment check failed: {msg}")
            show_error("Hermes UI Control - Error", msg)
            sys.exit(1)
        log("Environment OK")

        # Start tray
        from tray import run_tray

        # If --start flag, auto-start service before tray
        if auto_start:
            log("Auto-starting service...")
            import config as app_config
            run_mode = app_config.get("run_mode")
            if run_mode == "windows":
                import windows_manager
                threading.Thread(target=windows_manager.start, daemon=True).start()
            else:
                import wsl_manager
                threading.Thread(target=wsl_manager.start, daemon=True).start()

        log("Starting tray...")
        run_tray()

    finally:
        release_mutex()
        log("App exited")


if __name__ == "__main__":
    main()
