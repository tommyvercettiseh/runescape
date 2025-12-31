from __future__ import annotations

# 🔧 BOOTSTRAP: project-root eerst
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ✅ daarna pas project-imports
import random
from typing import Dict, List, Tuple

from ai_cursor import move_cursor          # ai_cursor staat in ROOT
from core.bot_offsets import (
    load_areas,
    apply_offset,
    get_bot_id,
    BOT_OFFSETS,
)


# =========================
# AREAS: cache
# =========================
AreasDict = Dict[str, List[int]]
_AREAS_CACHE: Dict[str, AreasDict] = {}


def _get_areas(pack: str | None = None) -> AreasDict:
    key = (pack or "").replace("\\", "/").strip() or "__default__"
    if key not in _AREAS_CACHE:
        _AREAS_CACHE[key] = load_areas(pack if key != "__default__" else None)
    return _AREAS_CACHE[key]


def move_to_area(
    area_name: str,
    *,
    bot_id: int | None = None,
    pack: str | None = None,
    duration: float = 0.55,   # 👈 trager zoals je self-test
    fps: int = 144,           # 👈 smoother
    padding: int = 3,
    center: bool = False,
) -> Tuple[int, int]:
    bot_id = int(bot_id if bot_id is not None else get_bot_id(1))
    areas = _get_areas(pack)

    if area_name not in areas:
        sample = ", ".join(list(areas.keys())[:10])
        raise KeyError(f"Area '{area_name}' niet gevonden. Voorbeeld areas: {sample}")

    x1, y1, x2, y2 = apply_offset(areas[area_name], bot_id)

    pad = max(0, int(padding))
    if (x2 - x1) <= 2 * pad or (y2 - y1) <= 2 * pad:
        pad = 0

    if center:
        x = (x1 + x2) // 2
        y = (y1 + y2) // 2
    else:
        x = random.randint(x1 + pad, x2 - pad)
        y = random.randint(y1 + pad, y2 - pad)

    move_cursor((x, y), duration=duration, fps=fps)
    return (x, y)


def move_in_area(
    area_name: str,
    bot_id: int = 1,
    pack: str | None = None,
    verbose: bool = True,
    duration: float = 0.55,   # 👈 zelfde als test
    fps: int = 144,
    jitter: float = 0.08,     # 👈 kleine variatie
) -> bool:
    areas = _get_areas(pack)

    area_key = area_name.lower()
    area_map = {k.lower(): k for k in areas}
    if area_key not in area_map:
        if verbose:
            print(f"❌ Gebied '{area_name}' niet gevonden")
        return False

    true_key = area_map[area_key]
    x1, y1, x2, y2 = apply_offset(areas[true_key], bot_id)

    rand_x = random.randint(x1, x2)
    rand_y = random.randint(y1, y2)

    # 👇 maak movement iets minder “robot”
    dur = max(0.12, float(duration) * random.uniform(1 - jitter, 1 + jitter))

    if verbose:
        ox, oy = BOT_OFFSETS.get(int(bot_id), (0, 0))
        print(f"🖱️ {true_key} -> ({rand_x},{rand_y}) offset ({ox},{oy}) dur={dur:.2f}s fps={fps}")

    move_cursor((rand_x, rand_y), duration=dur, fps=fps)
    return True

if __name__ == "__main__":
    print("\n🧪 move_to_area SELF TEST (Bot_Area)\nNiet bewegen met je muis 🙂\n")
    import time
    time.sleep(2)

    # 👇 Als Bot_Area in je default pack zit, laat pack=None
    # Als Bot_Area in een specifieke json zit, zet pack="mapje/bestand.json"
    pack = None  # bv: "skills/skills.json"

    # Debug: laat zien welke keys bestaan (handig als Bot_Area anders heet)
    areas = _get_areas(pack)
    print(f"📦 pack={pack or 'DEFAULT'} | areas loaded = {len(areas)}")
    print("🔎 eerste 20 areas:", list(areas.keys())[:20])

    # Probeer exact "Bot_Area"
    if "Bot_Area" not in areas:
        # case-insensitive zoeken
        hits = [k for k in areas.keys() if k.lower() == "bot_area"]
        if hits:
            print(f"✅ gevonden als '{hits[0]}' (case mismatch)")
            area_name = hits[0]
        else:
            # fuzzy suggesties
            sugg = [k for k in areas.keys() if "bot" in k.lower()]
            print("❌ 'Bot_Area' niet gevonden. Suggesties:", sugg[:20])
            raise SystemExit(1)
    else:
        area_name = "Bot_Area"

    # Test: beweeg 4 bots om de beurt
    for bot_id in (1, 2, 3, 4):
        print(f"\n🤖 Bot {bot_id} -> {area_name}")
        move_in_area(area_name, bot_id=bot_id, pack=pack, verbose=True)
        time.sleep(0.6)

    print("\n✅ klaar\n")
