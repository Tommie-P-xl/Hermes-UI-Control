"""Windows registry autostart management (no admin required)."""
import sys
import winreg

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
KEY_NAME = "HermesUIControl"


def _get_exe_path() -> str:
    """Return path to current executable (or python script if not frozen)."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return f'"{sys.executable}" "{__file__}"'


def enable():
    """Register app to start on Windows login."""
    exe = _get_exe_path()
    value = f'"{exe}" --minimize' if not exe.startswith('"') else f'{exe} --minimize'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, KEY_NAME, 0, winreg.REG_SZ, value)


def disable():
    """Remove app from Windows startup."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, KEY_NAME)
    except FileNotFoundError:
        pass


def is_enabled() -> bool:
    """Check if autostart is currently registered."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, KEY_NAME)
            return True
    except FileNotFoundError:
        return False
