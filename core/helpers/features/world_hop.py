from __future__ import annotations

import sys
import time
import random
from pathlib import Path

# ============================================================
# BOOTSTRAP 🚀
# ============================================================
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS 📥
# ============================================================
from core.move_to_area import move_in_area
from helpers.random_sleep import sleep_custom
from core.helpers import assist_click_tab

# ✅ AI MOUSE direct gebruiken
from core.ai_mouse.ai_mouse import human_click

# ✅ jouw keyboard engine
from core.ai_keyboard.ai_keyboard import type_text


# ============================================================
# ASSIST WORLD HOP 🌍
# ============================================================
def world_hop(bot_id: int = 1, verbose: bool = True) -> bool:
    verbose and print(f"🌍 World hop | bot {bot_id}")

    # Focus chat
    move_in_area("Chat_Area", bot_id=bot_id, verbose=False, padding=3)
    human_click(button="left", mode="safe_tap")
    sleep_custom(0.10, 0.22)

    # Typ hop command
    type_text("q", enter=True, scenario_label="chat_command")
    sleep_custom(0.08, 0.16)

    # Wachten tot hop klaar is
    hop_s = random.uniform(15, 35)
    verbose and print(f"⏳ Hopping... {hop_s:.1f}s")
    time.sleep(hop_s)

    # Terug naar inventory
    assist_click_tab("Inventory", bot_id=bot_id, verbose=verbose)

    verbose and print("✅ World hop done")
    return True

# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    while True:
        world_hop(bot_id=BOT_ID, verbose=True)
        time.sleep(0.3)

# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.features.world_hop