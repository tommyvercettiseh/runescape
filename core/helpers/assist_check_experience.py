from __future__ import annotations
import sys
from pathlib import Path
import math
import ctypes
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.move_to_area import move_in_area
from helpers.random_sleep import sleep_custom
from core.helpers.assist_click_tab import assist_click_tab

# onthoud rotatie per bot + skillset
_XP_ROT_STATE = {}


def assist_check_experience(*areas, bot_id=1, verbose=True):
    # =========================
    # INPUT CLEANUP 🧹
    # =========================
    cleaned = []
    for a in areas:
        s = str(a).strip()
        if s:
            cleaned.append(s)

    if not cleaned:
        verbose and print("⚠️  📊  Geen skill opgegeven")
        return False

    # =========================
    # PICK: 1 skill = die, 2+ = roteren 🔁
    # =========================
    if len(cleaned) == 1:
        area = cleaned[0]
        verbose and print(f"✅  📊  XP check   | {area}   (bot {bot_id})")
    else:
        key = f"{bot_id}|" + "|".join(cleaned)
        i = _XP_ROT_STATE.get(key, 0) % len(cleaned)
        area = cleaned[i]
        _XP_ROT_STATE[key] = i + 1
        verbose and print(f"✅  📊  XP rotatie | {area}   (bot {bot_id})")

    # =========================
    # ACTION 🎯
    # =========================
    verbose and print("⏳  🧭  Tab: Skilling openen")
    assist_click_tab("Skilling", bot_id=bot_id, verbose=verbose, timeout=3.0)
    verbose and print("✅  🧭  Tab: Skilling open")

    verbose and print(f"⏳  🧭  Naar area bewegen   | {area}")
    move_in_area(area, bot_id=bot_id, verbose=verbose)

    verbose and print("⏳  💤  Wachten")
    sleep_custom(1.5, 4.3)
    verbose and print("✅  💤  Wacht klaar")

    verbose and print("⏳  🎒  Tab: Inventory openen")
    assist_click_tab("Inventory", bot_id=bot_id, verbose=verbose, timeout=3.0)
    verbose and print("✅  🎒  Tab: Inventory open")

    return True


if __name__ == "__main__":
    print("🧪  Test assist_check_experience\n")

    # 1 skill
    assist_check_experience("Crafting", bot_id=1, verbose=True)
    print("\n🔁  Rotatie test\n")
    assist_check_experience("Woodcutting", "Fishing", bot_id=1, verbose=True)