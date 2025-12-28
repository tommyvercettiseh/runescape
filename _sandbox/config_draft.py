"""
config_draft.py

Doel
Laadt JSON configuraties (zoals areas.json en offsets.json) vanuit de project root.

Belangrijk
Werkt altijd, ook als je PowerShell in C:\\Windows\\System32 staat.
"""

from pathlib import Path
import json
import importlib.util
from typing import Any


def _import_paths_module() -> Any:
    """
    Importeert _sandbox/paths_draft.py via een absoluut pad,
    zodat imports niet afhankelijk zijn van sys.path of je huidige werkmap.
    """
    current_file_path = Path(__file__).resolve()
    paths_file_path = current_file_path.parent / "paths_draft.py"

    spec = importlib.util.spec_from_file_location("paths_draft", paths_file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Kan paths_draft.py niet importeren via: {paths_file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paths_module = _import_paths_module()
CONFIG_DIRECTORY = Path(paths_module.CONFIG_DIRECTORY)


def _read_json(file_path: Path) -> dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def try_load_json_file(filename: str) -> dict[str, Any]:
    file_path = CONFIG_DIRECTORY / filename
    if not file_path.exists():
        return {}
    return _read_json(file_path)


if __name__ == "__main__":
    print("✅ PROJECT_ROOT:", paths_module.PROJECT_ROOT)
    print("✅ CONFIG_DIRECTORY:", CONFIG_DIRECTORY)

    areas_path = CONFIG_DIRECTORY / "areas.json"
    offsets_path = CONFIG_DIRECTORY / "offsets.json"

    print("🔎 areas.json exists:", areas_path.exists(), "|", areas_path)
    print("🔎 offsets.json exists:", offsets_path.exists(), "|", offsets_path)

    areas_dictionary = try_load_json_file("areas.json")
    offsets_dictionary = try_load_json_file("offsets.json")

    print("📦 areas keys:", len(areas_dictionary))
    if areas_dictionary:
        print("   areas sample keys:", list(areas_dictionary.keys())[:5])

    print("📦 offsets keys:", len(offsets_dictionary))
    if offsets_dictionary:
        print("   offsets sample keys:", list(offsets_dictionary.keys())[:5])
