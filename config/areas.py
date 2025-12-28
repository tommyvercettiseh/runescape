from pathlib import Path
import json
from typing import Any

def load_area(area_root: Path, area_path: str) -> list[int]:
    """
    area_path voorbeeld:
    skills/inventory.slot_01
    """
    folder_part, key = area_path.split(".", 1)
    json_path = area_root / f"{folder_part}.json"

    if not json_path.exists():
        raise FileNotFoundError(f"Area file niet gevonden: {json_path}")

    with open(json_path, "r", encoding="utf-8") as file_handle:
        data: dict[str, Any] = json.load(file_handle)

    if key not in data:
        raise KeyError(f"Area key '{key}' niet gevonden in {json_path}")

    box = data[key]
    if not (isinstance(box, list) and len(box) == 4):
        raise ValueError(f"Ongeldige area box: {area_path}")

    return [int(v) for v in box]

from pathlib import Path
import json
from typing import Any

def load_area(area_root: Path, area_path: str) -> list[int]:
    """
    area_path voorbeeld:
    skills/inventory.slot_01
    """
    folder_part, key = area_path.split(".", 1)
    json_path = area_root / f"{folder_part}.json"

    if not json_path.exists():
        raise FileNotFoundError(f"Area file niet gevonden: {json_path}")

    with open(json_path, "r", encoding="utf-8") as file_handle:
        data: dict[str, Any] = json.load(file_handle)

    if key not in data:
        raise KeyError(f"Area key '{key}' niet gevonden in {json_path}")

    box = data[key]
    if not (isinstance(box, list) and len(box) == 4):
        raise ValueError(f"Ongeldige area box: {area_path}")

    return [int(v) for v in box]
print("📂 area_root:", area_root)
print("📄 json_path:", json_path)
print("🔑 key:", key)
