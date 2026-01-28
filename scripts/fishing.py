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
from core.click_colour import click_colour
from core.helpers.assist_inventory_full import inventory_full
from core.helpers.assist_banking import assist_banking
from core.helpers.assist_deposit import deposit_inventory
from core.helpers.assist_close_screen import assist_close_screen
from core.helpers.assist_target import assist_target
from ai_keyboard import press_key

# ============================================================
# SETTINGS
# ============================================================
BOT_ID =    1
TRACE =     False
VERBOSE =   False
DEBUG =     False
SKILL =     "Fishing"

# ============================================================
# HELPERS
# ============================================================
def main():

# CAN WE START? 
# ============================================================
    if not can_start(bot_id=BOT_ID, verbose=VERBOSE,trace=TRACE):
        return

# ARE WE SKILLING? 
# ============================================================
    if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
        print("✅ Skilling ")
        return

# ============================
# RANDOMIZATION 🎲
# ============================
    if random.random() < 0.01:
        VERBOSE and print("Checking experience 📊")
        assist_check_experience(SKILL, bot_id=BOT_ID, verbose=VERBOSE)

# IS OUR INVENTORY EMPTY? READY TO GO? 
# ============================================================

    if inventory_full(bot_id=BOT_ID,exclude_slots={1},exclude_images=["Item_SmallFishingNet.png","Item_Feathers.png","Item_FlyFishingRod.png"], verbose=VERBOSE):
        print ("LET. HIM. COOK🥘")
        if assist_target(kleur="rood", area="Bot_Area", bot_id=None, min_size=100, max_passes=2, verbose=VERBOSE):
            if not detect_image("Chat_Area_Corner.png", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE, timeout=8, interval=1.0):
                print("⛔ Image not found")
                drop_inventory( bot_id=BOT_ID,exclude_slots={1},exclude_images=["Item_SmallFishingNet.png","Item_Feathers.png","Item_FlyFishingRod.png"],trace=VERBOSE,debug=VERBOSE)
            else: 
                press_key("space")
                return

# LET'S COOK!
# ============================================================
    if not assist_click_target(kleur="paars", area="Bot_Area", bot_id=BOT_ID, min_size=200, verbose=VERBOSE):
        click_image("Icon_Fishing.png", "Info_Area", BOT_ID)
        return
    sleep_custom(2.1, 3.2)
    print("✅ Target found")
    return


if __name__ == "__main__":
     main()
