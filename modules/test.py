import sys
from pathlib import Path

# Zorg dat project-root in sys.path staat
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.template_profile import load_preset   # <-- NIEUW
from core.bot_offsets import load_areas
from vision.image_detection import detect_image


def main():
    areas = load_areas()
    preset = load_preset("jagex")

    print("Loaded preset:", preset)

    result = detect_image(
        image_path="jagex.png",
        area_name="FullScreen",
        method_name=preset["method_name"],
        vorm_drempel=preset["vorm_drempel"],
        kleur_drempel=preset["kleur_drempel"],
        bot_id=1,
        areas=areas
    )

    print("detect_image result:", result)


if __name__ == "__main__":
    main()
