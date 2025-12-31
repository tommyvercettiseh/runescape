import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.image_detection import detect_one
from ai_cursor import move_cursor


def main():
    template = "jagex.png"
    area = "FullScreen"
    bot_id = 1

    hit = detect_one(template, area_name=area, bot_id=bot_id)
    if not hit:
        print(f"❌ Niet gevonden: {template} in {area} (bot {bot_id})")
        return

    cx = hit.x + hit.width // 2
    cy = hit.y + hit.height // 2

    print(
        f"✅ Gevonden: {template} @ ({cx},{cy}) | "
        f"method={hit.method} vorm={hit.vorm}% kleur={hit.kleur}%"
    )

    move_cursor((cx, cy))


if __name__ == "__main__":
    main()
