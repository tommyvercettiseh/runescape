from pathlib import Path
import os


def _is_project_root(folder):
    return (
        (folder / "config").exists()
        and (folder / "assets").exists()
        and (folder / "_sandbox").exists()
    )


def find_project_root():
    here = Path(__file__).resolve()
    for p in (here.parent, *here.parents):
        if _is_project_root(p):
            return p
    return Path.cwd().resolve()


PROJECT_ROOT = Path(os.getenv("BOT_ROOT", "")).resolve() if os.getenv("BOT_ROOT") else find_project_root()

CONFIG_DIR = PROJECT_ROOT / "config"
ASSETS_DIR = PROJECT_ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
LOGS_DIR = PROJECT_ROOT / "logs"

__all__ = ["PROJECT_ROOT", "CONFIG_DIR", "ASSETS_DIR", "IMAGES_DIR", "LOGS_DIR"]


if __name__ == "__main__":
    print("ROOT:", PROJECT_ROOT)
    print("CONFIG:", CONFIG_DIR)
    print("IMAGES:", IMAGES_DIR)
    print("LOGS:", LOGS_DIR)
