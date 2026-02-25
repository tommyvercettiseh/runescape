from pathlib import Path
import sys
import os
from tabnanny import verbose
import time

# ============================================================
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
# ============================================================

# IMPORTS
# ============================================================

from core.helpers.assist_banking import assist_banking
from vision.image_detection import detect_image
from states.can_start_status import can_start
from core.helpers.assist_check_experience import assist_check_experience
from core.click_image import click_image, click_random_image
from core.helpers.assist_close_screen import assist_close_screen
from vision.colour_detection import detect_colour
from core.helpers.assist_click_target import assist_click_target
from helpers.random_sleep import sleep_custom
from core.click_colour import click_colour
from states.skilling_status import is_skilling

# ============================================================
BOT_ID = int(os.getenv("BOT_ID", "1"))
TRACE = False
VERBOSE = True
DEBUG = False
# ============================================================

def main():
    while True:
        if not can_start(bot_id=BOT_ID, verbose=VERBOSE, trace=TRACE):
            return

        if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
            return
        
        # =========================
        # BANKING: logs check
        # =========================
        if not detect_image("Item_Yew_Log.png", "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE):
            print("No logs found, banking...")
            if assist_banking(bot_id=BOT_ID, timeout_s=10, verbose=VERBOSE):
                if click_image("Item_Yew_Log.png", "Bot_Area", bot_id=BOT_ID, verbose=VERBOSE):
                    assist_close_screen(bot_id=BOT_ID, verbose=True)

        # =========================
        # FIRE CHECK: tile click
        # =========================
        if not detect_colour("paars", "Bot_Area", None, bot_id=BOT_ID, verbose=False, min_size=400):
            print("No fire, click tile")
            if click_image("Tile_Fire.png", "Bot_Area", bot_id=BOT_ID, button="left", verbose=VERBOSE):
                if not detect_image("Tile_Fire.png", "Bot_Area_Center", bot_id=BOT_ID, verbose=VERBOSE, timeout=5, interval=1.0):
                    if VERBOSE:
                        print("⛔ Tile niet zichtbaar in center.")
                else:
                    if VERBOSE:
                        print("✅ Tile in center found!")
                        if click_image("Item_Tinderbox.png", "Inventory_Area", bot_id=BOT_ID, button="left", verbose=VERBOSE):
                            if click_random_image("Item_Yew_Log.png", "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE):
                                sleep_custom(3.05, 8.12)
                                click_colour("paars", "Bot_Area", bot_id=BOT_ID, mode="deep_random", deep_erode_px=7, jitter_range=2, min_size=400, verbose=VERBOSE, trace=TRACE)
                                if not detect_image("Firemaking_Continue.png", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE, timeout=3, interval=1.0):
                                    verbose and print("⛔ Continue. Niet gevonden binnen 5s.")
                                    return False
                                sleep_custom(1.05, 2.12)
                            if click_image("Firemaking_Continue.png", "Chat_Area", bot_id=BOT_ID, button="left", verbose=VERBOSE):
                                verbose and print("✅ Fire made")
                                return
            else:
                if VERBOSE:
                    print("⛔ Tile click failed.")
        else:
            if VERBOSE: print("✅ Fire detected, let's burn logs!")
            if click_random_image("Item_Yew_Log.png", "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE):
                if click_colour("paars", "Bot_Area", bot_id=BOT_ID, mode="deep_random", deep_erode_px=7, jitter_range=2, min_size=400, verbose=VERBOSE, trace=TRACE):
                    if not detect_image("Firemaking_Continue.png", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE, timeout=10, interval=1.0):
                        verbose and print("⛔ Continue niet gevonden binnen 3s.")
                        return False
                    else:
                        click_image("Firemaking_Continue.png", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE)
                    sleep_custom(1.05, 2.12)
                    sleep_custom(4.05, 7.12)
                    return  
        time.sleep(0.05)  # tiny loop chill 😄

if __name__ == "__main__":
    main()
