from __future__ import annotations

from pathlib import Path
import os
import time


def _is_project_root(folder: Path) -> bool:
    return (folder / "config").exists() and (folder / "assets").exists()


def find_project_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here.parent, *here.parents):
        if _is_project_root(p):
            return p
    return Path.cwd().resolve()


def _resolve_bot_root() -> Path:
    env = os.getenv("BOT_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if _is_project_root(p):
            return p
    return find_project_root()


PROJECT_ROOT = _resolve_bot_root()

CONFIG_DIR = PROJECT_ROOT / "config"
ASSETS_DIR = PROJECT_ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
LOGS_DIR = PROJECT_ROOT / "logs"

AREAS_FILE = CONFIG_DIR / "areas.json"

# ✅ extra log subfolders
BOT_LOGS_DIR = LOGS_DIR / "bot_logs"
BOT_LOGS_DIR.mkdir(parents=True, exist_ok=True)

SCREENS_DIR = LOGS_DIR / "screens"
SCREENS_DIR.mkdir(parents=True, exist_ok=True)


def get_bot_log_file(bot_id: int, *, prefix: str = "bot", ts: str | None = None) -> Path:
    """
    Geef logfile pad voor een bot.
    Standaard: logs/bot_logs/bot_<id>_<timestamp>.log
    """
    bid = int(bot_id)
    stamp = ts or time.strftime("%Y-%m-%d_%H-%M-%S")
    return BOT_LOGS_DIR / f"{prefix}_{bid}_{stamp}.log"


__all__ = [
    "PROJECT_ROOT",
    "CONFIG_DIR",
    "ASSETS_DIR",
    "IMAGES_DIR",
    "LOGS_DIR",
    "AREAS_FILE",
    "BOT_LOGS_DIR",
    "SCREENS_DIR",
    "get_bot_log_file",
]


if __name__ == "__main__":
    print("ROOT:", PROJECT_ROOT)
    print("CONFIG:", CONFIG_DIR)
    print("ASSETS:", ASSETS_DIR)
    print("IMAGES:", IMAGES_DIR)
    print("AREAS :", AREAS_FILE)
    print("LOGS :", LOGS_DIR)
    print("BOT_LOGS:", BOT_LOGS_DIR)
    print("SCREENS:", SCREENS_DIR)
    print("EXAMPLE LOG:", get_bot_log_file(1))
