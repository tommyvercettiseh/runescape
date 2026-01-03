from __future__ import annotations

from pathlib import Path
import os


def _is_project_root(folder: Path) -> bool:
    return (folder / "config").exists() and (folder / "assets").exists()


def find_project_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here.parent, *here.parents):
        if _is_project_root(p):
            return p
    return Path.cwd().resolve()


def _resolve_bot_root() -> Path:
    env = os.getenv("BOT_ROOT", "")
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

__all__ = [
    "PROJECT_ROOT",
    "CONFIG_DIR",
    "ASSETS_DIR",
    "IMAGES_DIR",
    "LOGS_DIR",
    "AREAS_FILE",
]


if __name__ == "__main__":
    print("ROOT:", PROJECT_ROOT)
    print("CONFIG:", CONFIG_DIR)
    print("ASSETS:", ASSETS_DIR)
    print("IMAGES:", IMAGES_DIR)
    print("AREAS :", AREAS_FILE)
    print("LOGS :", LOGS_DIR)
