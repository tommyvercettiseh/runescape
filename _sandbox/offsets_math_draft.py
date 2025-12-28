from pathlib import Path
import os

def find_root(markers=("requirements.txt", ".git", "config", "assets")):
    here = Path(__file__).resolve()
    for p in (here.parent, *here.parents):
        if any((p / m).exists() for m in markers):
            return p
    return Path.cwd().resolve()

PROJECT_ROOT = Path(os.getenv("BOT_ROOT", "")).resolve() if os.getenv("BOT_ROOT") else find_root()

CONFIG_DIR = PROJECT_ROOT / "config"
ASSETS_DIR = PROJECT_ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
LOGS_DIR = PROJECT_ROOT / "logs"

if __name__ == "__main__":
    print("ROOT:", PROJECT_ROOT)
    print("CONFIG:", CONFIG_DIR)
    print("IMAGES:", IMAGES_DIR)
