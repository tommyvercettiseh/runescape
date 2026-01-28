# ============================================================
# BOOTSTRAP (altijd eerst)
# ============================================================
from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# SETTINGS
# ============================================================
BOT_ID = int(os.getenv("BOT_ID", "1"))
ITEM_IMAGE = os.getenv("ITEM_IMAGE", "Item_All_Logs.png").strip()  # (niet meer nodig voor droppen, maar ik laat 'm staan)

# ============================================================
# DROP INVENTORY CONFIG
# ============================================================
EXCLUDE_SLOTS = {
    1,
    # 28,
}

EXCLUDE_IMAGES = [
    "Item_Tinderbox.png",
    "Item_Axe.png",
]

# ============================================================
# IMPORTS (na bootstrap)
# ============================================================
import subprocess
import shutil
import time
import random

from core.helpers.assist_login import assist_login
from core.helpers.assist_logout import assist_logout
from states.should_play_status import should_play
from states.skilling_status import is_skilling
from core.helpers.assist_click_target import assist_click_target
from vision.image_detection import detect_image
from core.click_image import click_image
from helpers.random_sleep import sleep_custom, random_sleep
from core.helpers.assist_close_screen import assist_close_screen
from core.helpers.assist_exclude_bot import assist_click_exclude
from core.helpers.assist_check_experience import assist_check_experience
from core.helpers.assist_inventory import assist_inventory_empty
from core.helpers.assist_firemaking import assist_firemaking
from core.drop_inventory import drop_inventory
from states.can_start_status import can_start
from core.helpers.assist_click_tab import assist_click_tab  

# ============================================================
SKILL =         "Woodcutting"
SKILL_TWO =     "Firemaking"
VERBOSE =        False

# ============================================================
# MAIN LOOP
# ============================================================
def main():

    if not can_start(bot_id=BOT_ID, verbose=VERBOSE):
        return
    # 🚀 hier begint je echte script

    # ============================
    # CHAT CONTINUE 🚦
    # ============================
    if click_image("Chat_Area_ClickHereToContinue.png", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE):
        print("Continued chat ✅")

    if detect_image("Chat_Area_YourInventoryIsTooFull.png", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE):
        print("Aborting mission! 🚀")
        assist_click_exclude(bot_id=BOT_ID, verbose=VERBOSE)
        return

    if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
        return

    # ============================
    # RANDOMIZATION 🎲
    # ============================
    if random.random() < 0.01:
        VERBOSE and print("Checking experience 📊")
        assist_check_experience(SKILL, SKILL_TWO, bot_id=BOT_ID, verbose=VERBOSE)

    # ============================
    # INVENTORY CHECK 🚦
    # ============================
    assist_click_tab("Inventory", bot_id=BOT_ID, verbose=VERBOSE)
    if assist_inventory_empty(bot_id=BOT_ID, verbose=VERBOSE):
        VERBOSE and print("Inventory niet vol 🟢")
    else:
        print("Inventory vol 🔴 -> firemaking/drop flow")

        # ✅ Gate: alleen firemaking als tinderbox bestaat
        if detect_image("Item_Tinderbox.png", "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE):
            print("TINDERBOX GEVONDEN ✅ -> FIREMAKING 🔥")

            if not assist_firemaking(bot_id=BOT_ID, verbose=True):
                print("FIREMAKING FAILED ❌ -> DROP INVENTORY 🗑️")
                drop_inventory(
                    bot_id=BOT_ID,
                    dry_run=False,
                    exclude_slots=EXCLUDE_SLOTS,
                    exclude_images=EXCLUDE_IMAGES,
                    verbose=VERBOSE,
                )
            return

        print("GEEN TINDERBOX ❌ -> DROP INVENTORY 🗑️")
        drop_inventory(
            bot_id=BOT_ID,
            dry_run=False,
            exclude_slots=EXCLUDE_SLOTS,
            exclude_images=EXCLUDE_IMAGES,
            verbose=VERBOSE,
        )
        return

    assist_close_screen(bot_id=BOT_ID, verbose=VERBOSE)

    # ============================
    # CLICK TARGET
    # ============================
    if not assist_click_target(bot_id=BOT_ID, verbose=VERBOSE, min_size=1000):
        print("No target found 🏹")
        sleep_custom(2.1, 3.2)
        return


if __name__ == "__main__":
    main()
