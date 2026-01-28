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
# ============================================================
# SETTINGS
# ============================================================
BOT_ID = 1
SIZE = 400
TRACE = True
VERBOSE = True
COOK_ITEM = "Raw_Shrimps"

# ============================================================
# HELPERS
# ============================================================
def main():

# CAN WE START? 
# ============================================================
    if not can_start(bot_id=BOT_ID, verbose=VERBOSE):
        return

# ARE WE SKILLING? 
# ============================================================
    if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
        return
    
# IS OUR INVENTORY EMPTY? READY TO GO? 
# ============================================================

# LET'S COOK!
# ============================================================
    if assist_click_target(kleur="rood", area="Bot_Area", bot_id=1, min_size=50):
        print("Red found")
    else:
        print("Not found")

if __name__ == "__main__":
     main()
