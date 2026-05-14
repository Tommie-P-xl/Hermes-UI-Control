"""Configuration constants and persistent settings management."""
import json
from pathlib import Path

APP_NAME = "Hermes UI Control"
APP_VERSION = "1.0.3"
APP_AUTHOR = "HermesControl"

HERMES_PORT = 8648
HERMES_URL = f"http://localhost:{HERMES_PORT}"

# GitHub repo for auto-update (release assets)
GITHUB_OWNER = "Tommie-P-xl"
GITHUB_REPO = "Hermes-UI-Control"
UPDATE_CHECK_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

CONFIG_DIR = Path.home() / ".hermes-ui-control"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default settings
DEFAULTS = {
    "autostart": False,
    "auto_start_service": False,
    "notifications": True,
    "auto_update_check": True,
    "run_mode": "wsl",  # "wsl" or "windows"
}


def _ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load config from disk, merging with defaults."""
    _ensure_dir()
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict):
    """Persist config to disk."""
    _ensure_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get(key: str):
    """Get a single config value."""
    return load_config().get(key, DEFAULTS.get(key))


def set(key: str, value):
    """Set a single config value and persist."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
