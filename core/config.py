from pathlib import Path
import json

from core.paths import CONFIG_DIR


def load_json(filename, required=True):
    file_path = Path(CONFIG_DIR) / filename

    if not file_path.exists():
        if required:
            raise FileNotFoundError(f"Config niet gevonden: {file_path}")
        return {}

    with open(file_path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


if __name__ == "__main__":
    print("CONFIG_DIR:", CONFIG_DIR)

    areas = load_json("areas.json", required=True)
    offsets = load_json("offsets.json", required=True)

    print("areas keys:", len(areas) if isinstance(areas, dict) else "nvt")
    print("offsets keys:", len(offsets) if isinstance(offsets, dict) else "nvt")
