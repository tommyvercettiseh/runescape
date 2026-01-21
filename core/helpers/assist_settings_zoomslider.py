from __future__ import annotations
import sys
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from helpers.random_sleep import sleep_custom
from core.click_image import click_image
from core.move_to_area import move_in_area
from core.helpers.assist_click_tab import assist_click_tab
from core.helpers.assist_close_screen import assist_close_screen
from core.ai_cursor import click

# ======================================================================================================

def assist_settings_zoomslider(bot_id, verbose=True):
    if not assist_click_tab("Settings", bot_id=bot_id, verbose=verbose, timeout=3.0):
        return False

    if not click_image("Tab_Settings_AllSettings.png", "Inventory_Area", bot_id=bot_id, verbose=verbose):
        return False

    sleep_custom(1.2, 2.4)

    if not click_image("Tab_Settings_Display.png", "Bot_Area", bot_id=bot_id, verbose=verbose):
        return False

    sleep_custom(1.2, 2.4)

    if not move_in_area("Slider_Area", bot_id=bot_id, verbose=verbose):
        return False

    click()
    sleep_custom(1.2, 2.4)

    assist_close_screen(bot_id=bot_id, verbose=verbose)
    return True

# ======================================
# MAIN TEST
# ======================================
if __name__ == "__main__":
    BOT_ID = 1
    time.sleep(1.0)  # geeft je tijd om OSRS te focussen
    assist_settings_zoomslider(BOT_ID, verbose=True)

