import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
from core.paths import CONFIG_DIR
from core.bot_offsets import load_areas

from vision.image_detection import detect_one  # <- jouw vision package

META = Path(CONFIG_DIR) / "templates_meta.json"

def main():
    print("ROOT:", ROOT)
    print("CONFIG_DIR:", CONFIG_DIR)
    print("META exists:", META.exists(), "->", META)

    if META.exists():
        meta = json.loads(META.read_text(encoding="utf-8-sig"))
        print("META keys:", list(meta.keys()))
    else:
        meta = {}
        print("META missing!")

    areas = load_areas()
    print("AREA keys (first 20):", list(areas.keys())[:20])

    # Kies hier je test
    template = "jagex.png"
    area = list(areas.keys())[0]  # pakt automatisch de eerste area zodat je geen typefout maakt

    print("\nTEST template:", template)
    print("TEST area:", area)
    print("Preset for template:", meta.get(template))

    hit = detect_one(template, area_name=area, bot_id=1)
    print("\nRESULT hit:", hit)

if __name__ == "__main__":
    main()
