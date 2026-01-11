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
from ai_keyboard import hold_key_range  
from core.move_to_area import move_to_area
from helpers.random_sleep import sleep_custom
from core.ai_cursor import click

# ============================================================
# ============================================================
# ASSIST RESET CAMERA
# ============================================================

def assist_reset_camera(
    *,
    bot_id=1,
    key="left",
    min_sec=1.49,
    max_sec=1.72,
    verbose=True,
) -> bool:
    if verbose:
        print(f"🎥 Camera reset (bot {bot_id})")

    # 1) Naar compass bewegen en klikken
    move_to_area("Compass_Area", bot_id=bot_id)
    click()

    # kleine settle
    sleep_custom(1.2, 2.4)

    # 2) Camera draaien (key hold via params)
    if verbose:
        print(f"⌨️ Hold {key} tussen {min_sec:.2f}s en {max_sec:.2f}s")

    hold_key_range(key, min_sec, max_sec)

    # kleine settle erna
    sleep_custom(0.15, 0.35)

    if verbose:
        print("✅ Camera reset klaar")

    return True


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1

    assist_reset_camera(
        bot_id=BOT_ID,
        key="left",
        min_sec=1.49,
        max_sec=1.72,
        verbose=True,
    )
