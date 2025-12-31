import sys
from pathlib import Path

# Zorg dat project-root in sys.path staat
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bot_offsets import load_areas
from core.template_presets_store import load_preset
from vision.image_recognition import detect_image, detect_image_preset


def main():
    areas = load_areas()

    preset = load_preset("jagex")
    print("Loaded preset:", preset)

    print("Calling detect_image with preset...")
    result = detect_image(
        image_path="jagex.png",
        area_name="FullScreen",
        method_name=preset["method_name"],
        vorm_drempel=preset["vorm_drempel"],
        kleur_drempel=preset["kleur_drempel"],
        bot_id=1,
        areas=areas,
    )
    print("detect_image result:", result)

    print("Calling detect_image_preset shortcut...")
    result2 = detect_image_preset("jagex", "FullScreen", bot_id=1, areas=areas)
    print("detect_image_preset result:", result2)


if __name__ == "__main__":
    main()
