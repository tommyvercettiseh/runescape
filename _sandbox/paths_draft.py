"""
paths_draft.py

Doel
Bepaalt automatisch waar de project-root staat (de map 'Runescape').

Waarom
Dan kun je de hele map copy-pasten naar een andere pc of locatie,
zonder hardcoded paden.

Exports
PROJECT_ROOT
CONFIG_DIRECTORY
ASSETS_DIRECTORY
IMAGES_DIRECTORY
LOGS_DIRECTORY
"""

from pathlib import Path
import os


def _is_project_root(folder_path: Path) -> bool:
    has_config_folder = (folder_path / "config").exists()
    has_assets_folder = (folder_path / "assets").exists()
    has_sandbox_folder = (folder_path / "_sandbox").exists()
    return has_config_folder and has_assets_folder and has_sandbox_folder


def find_project_root() -> Path:
    current_file_path = Path(__file__).resolve()

    for parent_folder in (current_file_path.parent, *current_file_path.parents):
        if _is_project_root(parent_folder):
            return parent_folder

    return Path.cwd().resolve()


environment_root_value = os.getenv("BOT_ROOT", "").strip()
if environment_root_value:
    PROJECT_ROOT = Path(environment_root_value).resolve()
else:
    PROJECT_ROOT = find_project_root()

CONFIG_DIRECTORY = PROJECT_ROOT / "config"
ASSETS_DIRECTORY = PROJECT_ROOT / "assets"
IMAGES_DIRECTORY = ASSETS_DIRECTORY / "images"
LOGS_DIRECTORY = PROJECT_ROOT / "logs"

__all__ = [
    "PROJECT_ROOT",
    "CONFIG_DIRECTORY",
    "ASSETS_DIRECTORY",
    "IMAGES_DIRECTORY",
    "LOGS_DIRECTORY",
]

if __name__ == "__main__":
    print("ROOT:", PROJECT_ROOT)
    print("CONFIG:", CONFIG_DIRECTORY)
    print("IMAGES:", IMAGES_DIRECTORY)
    print("LOGS:", LOGS_DIRECTORY)
