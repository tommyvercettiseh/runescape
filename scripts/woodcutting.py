# ============================================================
# BOOTSTRAP (altijd eerst)
# ============================================================
from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
    
import os, sys
print("PYTHON:", sys.executable)
print("CWD:", os.getcwd())
print("ARGV:", sys.argv)
print("PATH0:", sys.path[0])
print("-" * 40)


# ============================================================
# SETTINGS
# ============================================================

BOT_ID = int(os.getenv("BOT_ID", "1"))

ITEM_IMAGE = os.getenv("ITEM_IMAGE", "Item_Willow_Logs.png").strip()

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
from helpers.random_sleep import random_sleep
from core.helpers.assist_click_target import assist_click_target 
from vision.image_detection import detect_image    
from core.click_image import click_images, click_image   
from helpers.random_sleep import sleep_custom, random_sleep
from core.ai_cursor import random_mouse_movement
from core.helpers.assist_click_tab import assist_click_tab  
from core.helpers.assist_close_screen import assist_close_screen
from core.helpers.assist_exclude_bot import assist_click_exclude
from core.helpers.assist_check_experience import assist_check_experience

# ============================================================

SKILL =     "Woodcutting"
VERBOSE =    False

# =========================
# ITEM TABLE
# =========================
ITEMS = {
    "Logs":     "Logs",
    "Willow":   "Willow_Logs",
    "Maple":    "Maple_Logs",
    "Yew":      "Yew_Logs",
    "Oak":      "Oak_Logs",
    "Redwood":  "Redwood_Logs",
}
# ============================================================
# MAIN LOOP 

def main():

    # ============================
    # LOGIN / LOGOUT
    # ============================

    Play = should_play(bot_id=BOT_ID, verbose=VERBOSE)
    if Play:
        assist_login(bot_id=BOT_ID, verbose=VERBOSE)
        if VERBOSE:
            print("Logged in ✅")
    else:
        assist_logout(bot_id=BOT_ID, verbose=VERBOSE)
        if VERBOSE:
            print("Logged out ✅")
        return

    # ============================
    # CHAT CONTINUE 🚦
    # ============================  
    if click_image("Chat_Area_ClickHereToContinue.png", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE):
        print("Continued chat ✅")

    if detect_image("Chat_Area_YourInventoryIsTooFull.png", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE):
        print("Aborting mission! 🚀")
        assist_click_exclude(bot_id=BOT_ID, verbose=VERBOSE)
        return

    assist_close_screen(bot_id=BOT_ID, verbose=VERBOSE)

    assist_click_tab("Inventory", bot_id=BOT_ID, verbose=VERBOSE, timeout=3.0)

    # ============================
    # SKILLING CHECK 🚦
    # ============================
    if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
        print("Skilling 🟢")
        return
    else:
        print("Not skilling 🔴")

    if random.random() < 0.10:
        if VERBOSE:
            print("Checking experience 📊")
        assist_check_experience(SKILL, bot_id=BOT_ID, verbose=VERBOSE)

    # ============================
    # INVENTORY CHECK 🚦
    # ============================
    if detect_image("Empty_Last_Spot.png", "Last_Inventory_Spot", bot_id=BOT_ID, verbose=VERBOSE):
        print("Last spot is empty 🟢")
    else:
        print("Last spot is not empty 🔴")
        if not click_images(ITEM_IMAGE,"Inventory_Area",bot_id=BOT_ID,verbose=VERBOSE,dry_run=False,skip_chance=0.061,seed=None):
            print("No inventory found to drop ❌")
            return
        
    # ============================
    # CLICK TARGET 
    # ============================
    if not assist_click_target(bot_id=BOT_ID, verbose=VERBOSE, min_size=1000):
        print("No target found 🏹")
        sleep_custom(2.1, 3.2)
        return

    # ============================
    # MAIN LOOP END
    # ============================

if __name__ == "__main__":
    main()
