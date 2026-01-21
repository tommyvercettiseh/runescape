# ============================================================
# BOOTSTRAP (altijd eerst)
# ============================================================
from pathlib import Path
import sys
import os
from tabnanny import verbose


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
from helpers.random_sleep import sleep_custom, random_sleep
from core.ai_cursor import random_mouse_movement
from core.helpers.assist_click_tab import assist_click_tab  
from core.helpers.assist_close_screen import assist_close_screen
from core.helpers.assist_exclude_bot import assist_click_exclude
from core.helpers.assist_check_experience import assist_check_experience
from core.move_to_area import move_in_area
# ============================================================

SKILL =     "Strength"
VERBOSE =    False

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
    # SKILLING CHECK 🚦
    # ============================
    if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
        print("Skilling 🟢")
        return
    else:
        print("Not skilling 🔴")

    if random.random() < 0.01:
        if VERBOSE:
            print("Checking experience 📊")
        assist_check_experience(SKILL, bot_id=BOT_ID, verbose=VERBOSE)
        
    # ============================
    # CLICK TARGET 
    # ============================
    if __name__ == "__main__":
        
    # ============================
        move_in_area("Bot_Area", bot_id=BOT_ID, verbose=VERBOSE)
        sleep_custom(0.1, 1.2)
        if assist_click_target(kleur="paars", area="Bot_Area", bot_id=BOT_ID, speed_pct=100,mode="random", verbose=VERBOSE, min_size=150, pick_strategy="nearest"):
            return
    # ============================
    # MAIN LOOP END
    # ============================

if __name__ == "__main__":
    main()

    
