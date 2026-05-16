"""System tray icon and menu for Hermes UI Control."""
import ctypes
import ctypes.wintypes
import struct
import threading
import time
import webbrowser
import winreg

import pystray
from PIL import Image, ImageDraw

from config import APP_NAME, APP_VERSION, HERMES_URL
from icon import get_icon_bytes
from main import log
import autostart
import updater
import config as app_config


def _is_system_dark_mode() -> bool:
    """Check if Windows system is using dark mode for apps."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except Exception:
        return False


# Preferred app mode constants for uxtheme
_APPEARANCE_LIGHT = 0
_APPEARANCE_DARK = 1
_APPEARANCE_FOLLOW_SYSTEM = 2

_uxtheme = ctypes.windll.uxtheme
# SetPreferredAppMode — ordinal 135 (Windows 10 1903+)
_SetPreferredAppMode = _uxtheme[135]
# FlushMenuThemes — ordinal 136 (Windows 10 1903+)
_FlushMenuThemes = _uxtheme[136]


def _enable_dark_mode_menus():
    """Enable dark mode for popup menus via uxtheme undocumented APIs."""
    try:
        _SetPreferredAppMode(_APPEARANCE_DARK)
        _FlushMenuThemes()
    except Exception:
        pass


def _disable_dark_mode_menus():
    """Restore system-default menu theming."""
    try:
        _SetPreferredAppMode(_APPEARANCE_FOLLOW_SYSTEM)
        _FlushMenuThemes()
    except Exception:
        pass


def _apply_dark_mode_to_hwnd(hwnd):
    """Apply immersive dark mode to a window via DWM API."""
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1)),
            ctypes.sizeof(ctypes.c_int),
        )
    except Exception:
        pass


def _get_manager():
    """Get the appropriate manager based on run mode."""
    run_mode = app_config.get("run_mode")
    if run_mode == "windows":
        import windows_manager
        return windows_manager
    else:
        import wsl_manager
        return wsl_manager

_icon: pystray.Icon | None = None
_status_state = "stopped"
_status_text = "未运行"
_update_info: dict | None = None
_polling = True

def _notify(title: str, message: str):
    """Show a Windows balloon notification via Shell_NotifyIconW (pure ctypes)."""
    cfg = app_config.load_config()
    if not cfg.get("notifications", True):
        return
    log(f"Notify: {title} - {message}")
    try:
        # NOTIFYICONDATAW structure for balloon notification
        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint),
                ("hWnd", ctypes.c_void_p),
                ("uID", ctypes.c_uint),
                ("uFlags", ctypes.c_uint),
                ("uCallbackMessage", ctypes.c_uint),
                ("hIcon", ctypes.c_void_p),
                ("szTip", ctypes.c_wchar * 128),
                ("dwState", ctypes.c_uint),
                ("dwStateMask", ctypes.c_uint),
                ("szInfo", ctypes.c_wchar * 256),
                ("uTimeoutOrVersion", ctypes.c_uint),
                ("szInfoTitle", ctypes.c_wchar * 64),
                ("dwInfoFlags", ctypes.c_uint),
                ("guidItem", ctypes.c_byte * 16),
                ("hBalloonIcon", ctypes.c_void_p),
            ]

        NIM_ADD = 0x00000000
        NIM_MODIFY = 0x00000001
        NIM_DELETE = 0x00000002
        NIF_ICON = 0x00000002
        NIF_TIP = 0x00000004
        NIF_INFO = 0x00000010
        NIIF_NONE = 0x00000000
        NIIF_INFO = 0x00000001

        # Use pystray's HWND and uID to modify the existing icon
        hwnd = 0
        uid = 0
        if _icon and hasattr(_icon, "_hwnd"):
            hwnd = _icon._hwnd
        if _icon and hasattr(_icon, "_uid"):
            uid = _icon._uid

        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = hwnd
        nid.uID = uid
        nid.uFlags = NIF_INFO
        nid.szInfoTitle = title[:63]
        nid.szInfo = message[:255]
        nid.dwInfoFlags = NIIF_INFO

        # Modify existing icon to show balloon notification (no extra icon created)
        ctypes.windll.shell32.Shell_NotifyIconW(NIM_MODIFY, nid)
        log("Notify: Shell_NotifyIconW called")
    except Exception as e:
        log(f"Notify error: {type(e).__name__}: {e}")


def _create_status_icon(state: str) -> Image.Image:
    """Create a dynamic icon with status indicator."""
    base = Image.open(
        __import__("io").BytesIO(get_icon_bytes())
    ).convert("RGBA")
    base = base.resize((256, 256), Image.LANCZOS)

    draw = ImageDraw.Draw(base)
    dot_color = {
        "running": (76, 175, 80),
        "stopped": (158, 158, 158),
        "starting": (255, 193, 7),
    }.get(state, (158, 158, 158))

    cx, cy, r = 220, 220, 32
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=dot_color)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=6)

    return base


def _refresh_menu():
    """Rebuild and update the tray menu to reflect current state."""
    if _icon:
        _icon.menu = _build_menu()


def _update_icon_state():
    """Periodically check status and update tray icon."""
    global _status_state, _status_text, _polling

    while _polling:
        try:
            manager = _get_manager()
            state = manager.get_status_icon_state()
            if state != _status_state:
                _status_state = state
                if state == "running":
                    _status_text = f"运行中 {HERMES_URL}"
                else:
                    _status_text = "未运行"
                if _icon:
                    _icon.icon = _create_status_icon(state)
                    _icon.title = f"{APP_NAME} v{APP_VERSION}\n{_status_text}"
                    _refresh_menu()
        except Exception:
            pass
        time.sleep(3)


def _on_start(icon, item):
    """Start hermes-web-ui."""
    global _status_state
    log("Menu: Start clicked")
    _status_state = "starting"
    icon.icon = _create_status_icon("starting")
    icon.title = f"{APP_NAME} v{APP_VERSION}\n启动中..."
    _refresh_menu()

    def _do():
        global _status_state
        try:
            manager = _get_manager()
            log("Thread: calling manager.start()")
            result = manager.start()
            log(f"Thread: start() returned: {result}")
            # Verify actual port state instead of blindly assuming success
            if manager.is_port_open():
                _status_state = "running"
                _notify("Hermes UI Control", "服务已启动")
            else:
                _status_state = "stopped"
                _notify("Hermes UI Control", "启动超时，服务可能未就绪")
        except Exception as e:
            log(f"Thread: start() error: {type(e).__name__}: {e}")
            _status_state = "stopped"
            _notify("Hermes UI Control", f"启动失败: {e}")
        _refresh_menu()

    threading.Thread(target=_do, daemon=True).start()


def _on_stop(icon, item):
    """Stop hermes-web-ui."""
    global _status_state
    log("Menu: Stop clicked")
    _status_state = "stopped"
    _refresh_menu()

    def _do():
        global _status_state
        try:
            manager = _get_manager()
            log("Thread: calling manager.stop()")
            manager.stop()
            log("Thread: stop() done")
            _notify("Hermes UI Control", "服务已停止")
        except Exception as e:
            log(f"Thread: stop() error: {type(e).__name__}: {e}")
        _status_state = "stopped"
        _refresh_menu()

    threading.Thread(target=_do, daemon=True).start()


def _on_restart(icon, item):
    """Restart hermes-web-ui."""
    global _status_state
    log("Menu: Restart clicked")
    _status_state = "starting"
    icon.icon = _create_status_icon("starting")
    _refresh_menu()

    def _do():
        global _status_state
        try:
            manager = _get_manager()
            log("Thread: calling manager.restart()")
            result = manager.restart()
            log(f"Thread: restart() returned: {result}")
            # Verify actual port state instead of blindly assuming success
            if manager.is_port_open():
                _status_state = "running"
                _notify("Hermes UI Control", "服务已重启")
            else:
                _status_state = "stopped"
                _notify("Hermes UI Control", "重启超时，服务可能未就绪")
        except Exception as e:
            log(f"Thread: restart() error: {type(e).__name__}: {e}")
            _status_state = "stopped"
        _refresh_menu()

    threading.Thread(target=_do, daemon=True).start()


def _on_open_browser(icon, item):
    """Open browser to hermes URL."""
    manager = _get_manager()
    manager.open_browser()


def _on_toggle_autostart(icon, item):
    """Toggle Windows autostart."""
    cfg = app_config.load_config()
    if cfg.get("autostart"):
        autostart.disable()
        cfg["autostart"] = False
    else:
        autostart.enable()
        cfg["autostart"] = True
    app_config.save_config(cfg)
    _refresh_menu()


def _on_toggle_auto_service(icon, item):
    """Toggle auto-start service on app launch."""
    cfg = app_config.load_config()
    cfg["auto_start_service"] = not cfg.get("auto_start_service", False)
    app_config.save_config(cfg)
    _refresh_menu()


def _on_toggle_notifications(icon, item):
    """Toggle popup notifications."""
    cfg = app_config.load_config()
    cfg["notifications"] = not cfg.get("notifications", True)
    app_config.save_config(cfg)
    _refresh_menu()


def _on_switch_to_wsl(icon, item):
    """Switch to WSL mode."""
    cfg = app_config.load_config()
    cfg["run_mode"] = "wsl"
    app_config.save_config(cfg)
    _notify("Hermes UI Control", "已切换到 WSL 模式")
    _refresh_menu()


def _on_switch_to_windows(icon, item):
    """Switch to Windows native mode."""
    cfg = app_config.load_config()
    cfg["run_mode"] = "windows"
    app_config.save_config(cfg)
    _notify("Hermes UI Control", "已切换到 Windows 模式")
    _refresh_menu()


def _on_check_update(icon, item):
    """Check for updates in background."""
    global _update_info

    def _do():
        global _update_info
        info = updater.check_for_update()
        _update_info = info
        if info:
            _refresh_menu()
            _notify("Hermes UI Control", f"发现新版本: {info['version']}")
        else:
            _notify("Hermes UI Control", "已是最新版本")

    threading.Thread(target=_do, daemon=True).start()


def _on_do_update(icon, item):
    """Perform the update."""
    global _update_info
    if _update_info and _update_info.get("url"):
        _notify("Hermes UI Control", f"正在下载更新 {_update_info['version']}...")
        try:
            success = updater.perform_update(_update_info["url"])
        except Exception as e:
            log(f"Update error: {type(e).__name__}: {e}")
            success = False
        if success:
            icon.stop()
        else:
            _update_info = None
            _refresh_menu()
            _notify("Hermes UI Control", "更新失败，正在打开下载页面...")
            webbrowser.open(f"https://github.com/{app_config.GITHUB_OWNER}/{app_config.GITHUB_REPO}/releases/latest")


def _on_quit(icon, item):
    """Quit the application — also stop services."""
    global _polling
    log("Menu: Quit clicked, stopping services...")
    _polling = False

    # Stop hermes before exiting
    def _cleanup():
        try:
            manager = _get_manager()
            manager.stop()
            log("Cleanup: services stopped")
        except Exception as e:
            log(f"Cleanup error: {e}")

    _cleanup()
    icon.stop()


def _build_menu():
    """Build the dynamic tray menu based on current state."""
    cfg = app_config.load_config()
    is_running = _status_state == "running"
    is_starting = _status_state == "starting"
    run_mode = cfg.get("run_mode", "wsl")

    items = [
        pystray.MenuItem("启动服务", _on_start, enabled=not is_running and not is_starting),
        pystray.MenuItem("停止服务", _on_stop, enabled=is_running or is_starting),
        pystray.MenuItem("重启服务", _on_restart, enabled=is_running),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("打开浏览器", _on_open_browser, enabled=is_running),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "运行模式",
            pystray.Menu(
                pystray.MenuItem("WSL 模式", _on_switch_to_wsl, checked=lambda item: app_config.load_config().get("run_mode", "wsl") == "wsl"),
                pystray.MenuItem("Windows 模式", _on_switch_to_windows, checked=lambda item: app_config.load_config().get("run_mode", "wsl") == "windows"),
            )
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("开机自启动", _on_toggle_autostart, checked=lambda item: app_config.load_config().get("autostart", False)),
        pystray.MenuItem("启动时自动开启服务", _on_toggle_auto_service, checked=lambda item: app_config.load_config().get("auto_start_service", False)),
        pystray.MenuItem("弹窗通知", _on_toggle_notifications, checked=lambda item: app_config.load_config().get("notifications", True)),
        pystray.Menu.SEPARATOR,
    ]

    if _update_info:
        items.append(pystray.MenuItem(f"更新可用: {_update_info['version']}", _on_do_update))
    else:
        items.append(pystray.MenuItem("检查更新", _on_check_update))

    items.extend([
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"退出 (v{APP_VERSION})", _on_quit),
    ])

    return pystray.Menu(*items)


WM_RBUTTONUP = 0x0205


def _patch_menu_for_dark_mode(icon):
    """Patch the icon to apply dark mode to popup menus.

    Strategy:
    1. Use uxtheme SetPreferredAppMode to enable dark menus at app level
    2. Apply DWM dark mode to the menu owner window
    3. Re-apply before each right-click menu show
    """
    if not _is_system_dark_mode():
        return

    try:
        impl = icon._impl

        # Enable dark mode for menus globally
        _enable_dark_mode_menus()

        # Apply DWM dark mode to the icon windows
        if hasattr(impl, '_hwnd') and impl._hwnd:
            _apply_dark_mode_to_hwnd(impl._hwnd)
        if hasattr(impl, '_menu_hwnd') and impl._menu_hwnd:
            _apply_dark_mode_to_hwnd(impl._menu_hwnd)

        # Hook _on_notify to ensure dark mode is applied before each menu show
        if hasattr(impl, '_on_notify'):
            original_on_notify = impl._on_notify

            def _dark_on_notify(wparam, lparam):
                if lparam == WM_RBUTTONUP:
                    _enable_dark_mode_menus()
                    if impl._menu_hwnd:
                        _apply_dark_mode_to_hwnd(impl._menu_hwnd)
                return original_on_notify(wparam, lparam)

            impl._on_notify = _dark_on_notify
            log("Dark mode menu patch applied")
    except Exception as e:
        log(f"Dark mode patch failed: {e}")


def run_tray():
    """Create and run the system tray icon."""
    global _icon

    initial_icon = _create_status_icon("stopped")
    _icon = pystray.Icon(
        name="HermesUIControl",
        icon=initial_icon,
        title=f"{APP_NAME} v{APP_VERSION}\n未运行",
        menu=_build_menu(),
    )

    _patch_menu_for_dark_mode(_icon)

    poll_thread = threading.Thread(target=_update_icon_state, daemon=True)
    poll_thread.start()

    # Notify app started
    _notify("Hermes UI Control", f"已启动 (v{APP_VERSION})")

    cfg = app_config.load_config()
    if cfg.get("auto_start_service"):
        manager = _get_manager()
        threading.Thread(target=manager.start, daemon=True).start()

    _icon.run()
