# ============================================================
# BOOTSTRAP
# ============================================================

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
from core.ai_cursor import click
from core.move_to_area import move_to_area
from helpers.random_sleep import sleep_custom


# ============================================================
# ASSIST RESET CAMERA
# WAT: Cursor random in Bot_Area + menselijk uitzoomen
# WAAROM: View reset zodat interacties (bank/target) beter zichtbaar worden
# ============================================================
# ============================================================

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # Runescape/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
import pyautogui
from ai_keyboard import hold_key_range
from core.ai_cursor import click
from core.move_to_area import move_to_area
from helpers.random_sleep import sleep_custom

# ============================================================
# BANK PRESETS
# ============================================================

def bank(key, min_sec, max_sec):
    return {
        "key": key,
        "min_sec": min_sec,
        "max_sec": max_sec,
    }

BANK_PRESETS = {
    "Edgeville": bank("left", 1.49, 1.72),
    "Varrock": bank("left", 1.49, 1.72),
    "Grand Exchange": bank("left", 1.49, 1.72),
    "Falador": bank("left", 1.49, 1.72),
    "Al Kharid": bank("left", 1.49, 1.72),
}


# ============================================================
# SCROLL STANDARD
# ============================================================

SCROLL_TICKS = 16
SCROLL_AMOUNT = -240   # negatief = uitzoomen

def standard_scroll(verbose=True):
    # =========================
    # S) Standaard scroll
    # =========================
    # Altijd dezelfde vaste scroll stap.
    if verbose:
        print(f"🌀 Scroll: {SCROLL_TICKS} ticks")

    for _ in range(SCROLL_TICKS):
        pyautogui.scroll(SCROLL_AMOUNT)
        sleep_custom(0.03, 0.09)


# ============================================================
# ASSIST RESET CAMERA
# ============================================================

def assist_reset_camera(
    *,
    bot_id=1,
    bank_name="Edgeville",
    key=None,
    min_sec=None,
    max_sec=None,
    verbose=True,
):
    if verbose:
        print(f"🎥 Camera reset | Bank={bank_name} | Bot={bot_id}")

    # =========================
    # 1) Preset ophalen
    # =========================
    preset = BANK_PRESETS.get(bank_name, bank("left", 1.4, 1.7))

    key = key or preset["key"]
    min_sec = min_sec or preset["min_sec"]
    max_sec = max_sec or preset["max_sec"]

    if verbose:
        print(f"🏦 Preset | key={key} | {min_sec:.2f}s → {max_sec:.2f}s")

    # =========================
    # 2) Naar compass + klik
    # =========================
    move_to_area("Compass_Area", bot_id=bot_id)
    click()
    sleep_custom(1.2, 2.4)

    # =========================
    # 3) Camera draaien (key hold)
    # =========================
    hold_key_range(key, min_sec, max_sec)
    sleep_custom(0.15, 0.35)

    # =========================
    # 4) Standaard scroll
    # =========================
    move_to_area("Bot_Area", bot_id=bot_id)
    standard_scroll(verbose=verbose)
    sleep_custom(0.10, 0.25)

    if verbose:
        print("✅ Camera reset klaar")

    return True


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    BOT_ID = 1
    assist_reset_camera(bot_id=BOT_ID, bank_name="Edgeville", verbose=True)
