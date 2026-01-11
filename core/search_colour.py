from __future__ import annotations

import sys
import time
import random
from pathlib import Path

import pyautogui

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.move_to_area import move_to_area
from core.click_colour import has_colour_in_area
from ai_keyboard import press_key, hold_key_range


ZOOM_UNITS_MAX = 50
CHAT_AREA = "Chat_Area"   # pas aan als anders


def _log(verbose, msg):
    if verbose == "on":
        print(msg)


def _scroll_units(units):
    remaining = abs(units)
    direction = 1 if units > 0 else -1

    while remaining > 0:
        burst = min(remaining, random.randint(10, 22))

        for _ in range(burst):
            step = random.choices([1, 2, 3], weights=[0.70, 0.27, 0.03])[0] * direction
            pyautogui.scroll(step)
            time.sleep(random.uniform(0.015, 0.020))

        remaining -= burst
        time.sleep(random.uniform(0.06, 0.12))


def search_colour(KLEUR, BOT_AREA, BOT_ID=1, MAX_SEC=8, VERBOSE="on"):
    start = time.time()
    tries = 0

    _log(VERBOSE, f"\n🔎 search_colour kleur={KLEUR} bot_area={BOT_AREA} bot={BOT_ID}")

    # =========================
    # 1) Focus window via CHAT_AREA
    # =========================
    _log(VERBOSE, "🖱️ focus window (CHAT_AREA)")
    move_to_area(CHAT_AREA, bot_id=BOT_ID)
    time.sleep(random.uniform(0.12, 0.22))

    pyautogui.click()  # hard focus op browser window
    time.sleep(random.uniform(0.15, 0.30))

    # =========================
    # 2) Focus player via BOT_AREA
    # =========================
    _log(VERBOSE, "🖱️ focus player (BOT_AREA)")
    move_to_area(BOT_AREA, bot_id=BOT_ID)
    time.sleep(random.uniform(0.12, 0.22))

    pyautogui.click()  # dit is de belangrijkste click
    time.sleep(random.uniform(0.15, 0.30))

    # =========================
    # 3) Quick input test (als dit niks doet -> focus/permissions issue)
    # =========================
    _log(VERBOSE, "🧪 test input: klein scroll + 1x LEFT")
    pyautogui.scroll(-3)
    time.sleep(random.uniform(0.08, 0.14))
    press_key("left")
    time.sleep(random.uniform(0.10, 0.18))

    # =========================
    # 4) Reset view
    # =========================
    _log(VERBOSE, "🔍 zoom out")
    _scroll_units(-ZOOM_UNITS_MAX)

    _log(VERBOSE, "⬆️ hoogste punt")
    hold_key_range("up", 1.50, 1.85)
    time.sleep(random.uniform(0.10, 0.18))

    # =========================
    # 5) Scan links/rechts
    # =========================
    while (time.time() - start) < MAX_SEC:
        tries += 1

        if has_colour_in_area(KLEUR, BOT_AREA, BOT_ID):
            _log(VERBOSE, f"🎯 FOUND tries={tries}")
            return "FOUND"

        press_key(random.choice(["left", "right"]))

        if random.random() < 0.18:
            hold_key_range("up", 0.10, 0.25)

        time.sleep(random.uniform(0.10, 0.22))

    _log(VERBOSE, f"⌛ NOT FOUND tries={tries}")
    return None


if __name__ == "__main__":
    search_colour("paars", "Bot_Area", 1, 8, "on")
