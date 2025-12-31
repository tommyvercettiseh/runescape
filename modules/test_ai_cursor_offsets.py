from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bot_offsets import load_areas, apply_offset
from ai_cursor import move_cursor

AREAS = load_areas()
AREA = "Bot_Area"   # neem een duidelijke area
SLEEP = 1.5


def center_of(box):
    x1, y1, x2, y2 = box
    return (x1 + x2) // 2, (y1 + y2) // 2


if __name__ == "__main__":
    print("🎯 AI CURSOR OFFSET TEST\n")

    for bot_id in (1, 2, 3, 4):
        base = AREAS[AREA]
        shifted = apply_offset(base, bot_id)
        cx, cy = center_of(shifted)

        print(f"🤖 Bot {bot_id}")
        print(f"   base   = {base}")
        print(f"   shifted= {shifted}")
        print(f"   move → ({cx}, {cy})")

        move_cursor((cx, cy))
        time.sleep(SLEEP)

    print("\n✅ Klaar")
