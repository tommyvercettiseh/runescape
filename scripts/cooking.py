# ============================================================
# BOOTSTRAP (altijd eerst)
# ============================================================
from pathlib import Path
import sys
import os

from core.helpers.assist_banking import assist_banking

ROOT = Path(__file__).resolve().parents[2]
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
from ai_keyboard import press_key

# ============================================================
# SETTINGS
# ============================================================
BOT_ID = 1
TRACE = True
VERBOSE = True

# ============================================================
# MAIN
# ============================================================
def main():
    assist_banking(bot_id=BOT_ID, timeout_s=10, verbose=True)
# CLICK TARGET
# ============================================================
    if assist_click_target(kleur="rood", area="Bot_Area", bot_id=BOT_ID, min_size=100, verbose=VERBOSE):
        print("Red found")
    else:
        return

# CLICK TARGET
# ============================================================
    if not detect_image("Chat_Area_Corner.png", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE, timeout=15, interval=1.0):
        print("⛔ Image not found")
        return False
    else: 
        press_key("space")

# PLAY MAIN
# ============================================================
if __name__ == "__main__":
     main()
