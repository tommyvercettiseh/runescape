# ============================================================
# BOOTSTRAP
# ============================================================
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # Runescape/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
import random
import pyautogui

from core.move_to_area import move_to_area
from helpers.random_sleep import sleep_custom


# ============================================================
# ASSIST RESET CAMERA
# WAT: Cursor random in Bot_Area + menselijk uitzoomen
# WAAROM: View reset zodat interacties (bank/target) beter zichtbaar worden
# ============================================================
def assist_reset_camera(*, bot_id=1, scroll_ticks=20, verbose=True) -> bool:
    if verbose:
        print(f"🎥 Camera reset (bot {bot_id})")

    # 1) Cursor RANDOM in Bot_Area (geen center, geen bias)
    move_to_area(
        "Bot_Area",
        bot_id=bot_id,
        duration=0.45,
        fps=144,
        padding=6,
    )

    # korte settle
    sleep_custom(0.15, 0.35)

    # 2) Uitzoomen (menselijk: bursts + variabele scroll amounts + micro pauzes)
    remaining = int(scroll_ticks)

    while remaining > 0:
        burst = 1
        if remaining >= 4 and random.random() < 0.25:
            burst = random.randint(2, 4)

        steps = min(burst, remaining)
        for _ in range(steps):
            amount = random.choice([-180, -240, -300, -360])  # negatief = uitzoomen
            pyautogui.scroll(amount)

            # micro timing (geen 2-9s ellende)
            sleep_custom(0.03, 0.09)

            # soms even "kijken"
            if random.random() < 0.15:
                sleep_custom(0.08, 0.18)

        remaining -= steps

        # mini pauze tussen bursts
        if remaining > 0 and random.random() < 0.20:
            sleep_custom(0.10, 0.25)

    if verbose:
        print("✅ Camera reset klaar")

    return True


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    ok = assist_reset_camera(bot_id=BOT_ID, scroll_ticks=20, verbose=True)
    print("RESULT:", ok)
