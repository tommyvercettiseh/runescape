from pathlib import Path
import sys
import os
import time
import random



# ============================================================
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
# ============================================================

# IMPORTS
# ============================================================
from ai_keyboard import press_key
from core.helpers.assist_click_tab import assist_click_tab 
from core.helpers.assist_banking import assist_banking
from vision.image_detection import detect_image
from states.can_start_status import can_start
from core.helpers.assist_check_experience import assist_check_experience
from core.click_image import click_image, click_random_image
from core.helpers.assist_close_screen import assist_close_screen
from vision.colour_detection import detect_colour
from core.helpers.assist_click_target import assist_click_target
from core.helpers.assist_deposit import deposit_inventory
from helpers.random_sleep import sleep_custom
from core.click_colour import click_colour
from states.skilling_status import is_skilling
from core.move_to_area import move_in_area

# ============================================================
BOT_ID = int(os.getenv("BOT_ID", "1"))
TRACE = False
VERBOSE = False
DEBUG = False
SKILL = "Herblore"
ITEM_1 = "Ranarr_Potion"
ITEM_2 = "Snape_Grass"  
CONTINUE = "Herblore_Potion_Continue.png"

# ============================================================

def main():
    while True:
        # ============================================================
        # ✅ Safety gate
        # ============================================================
        assist_close_screen(bot_id=BOT_ID, verbose=VERBOSE)
        if not can_start(bot_id=BOT_ID, verbose=VERBOSE, trace=TRACE):
            return

        # ============================================================
        # 🧠 State gate
        # ============================================================
        if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
            VERBOSE and print("🧠 Already skilling, exiting main loop.")
            return

        time.sleep(random.triangular(2.51, 3.12, 15.23))

        # ============================================================
        # 🎲 Random human-check
        # ============================================================
        if random.random() < 0.03:
            VERBOSE and print("📊 Random check: opening XP/skill panel...")
            assist_check_experience(SKILL, bot_id=BOT_ID, verbose=VERBOSE)

        # ============================================================
        # 🎒 UI prep
        # ============================================================
        if assist_click_tab("Inventory", bot_id=BOT_ID, verbose=VERBOSE):
            VERBOSE and print("✅  Inventory tab selected ")
        else:
            VERBOSE and print("⚠️ Failed to select Inventory tab")
            continue

        # =========================
        # Inventory check
        # =========================

        if (
            not detect_image(f"Item_{ITEM_1}.png", "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE)
            or
            not detect_image(f"Item_{ITEM_2}.png", "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE)
        ):
            print("Supplies missing!")

            if assist_banking(bot_id=BOT_ID, timeout_s=10, verbose=VERBOSE):
                deposit_inventory(bot_id=BOT_ID)
                if click_image(f"Item_{ITEM_1}.png", "Bot_Area", bot_id=BOT_ID, verbose=VERBOSE):
                    if click_image(f"Item_{ITEM_2}.png", "Bot_Area", bot_id=BOT_ID, verbose=VERBOSE):
                        if assist_close_screen(bot_id=BOT_ID, verbose=VERBOSE):
                            continue
            return False
        
# MIXING TWO ITEMS 
# =========================

        if not click_random_image(f"Item_{ITEM_1}.png", "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE):
            return False
        print(f"Clicked {ITEM_1}")

        if not click_random_image(f"Item_{ITEM_2}.png", "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE):
            return False
        print(f"Clicked {ITEM_2}")
        
        if not detect_image(f"{CONTINUE}", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE, timeout=5, interval=1.0):
            return False

        else:
            if random.random() < 0.72:
                if click_image(f"{CONTINUE}", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE):
                    sleep_custom(1.5, 2.5)
            else:
                press_key("space")
                print("Pressed spacebar.")
        move_in_area("Offscreen", bot_id=BOT_ID, verbose=VERBOSE)
    
if __name__ == "__main__":
    main()
