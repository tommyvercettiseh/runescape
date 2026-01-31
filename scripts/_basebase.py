# ============================================================
# BOOTSTRAP 📂
# ============================================================
from pathlib import Path
import sys
import os
import random

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# SETTINGS ⚙️
# ============================================================
BOT_ID = int(os.getenv("BOT_ID", "1"))
SKILL = os.getenv("SKILL", "Fishing").strip()

TRACE = False
VERBOSE = False
DEBUG = False

# ============================================================

EXCLUDE_SLOTS = {1}

EXCLUDE_IMAGES = [
    "Item_SmallFishingNet.png",
    "Item_Feathers.png",
    "Item_FlyFishingRod.png",
]

# ============================================================
# AUTOLOAD 🧠 
# ============================================================
from core.autoload import autoload
autoload(globals(), verbose=VERBOSE)

# ============================================================
# START 🧱
# ============================================================
def main():

# CAN WE START? 
# ============================================================
    if not can_start(bot_id=BOT_ID, verbose=VERBOSE, trace=TRACE):
        return

# ARE WE SKILLING? 
# ============================================================
    if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
        return
    
# IS OUR INVENTORY EMPTY? READY TO GO?
# ============================================================
    if inventory_full(bot_id=BOT_ID,exclude_slots=EXCLUDE_SLOTS,exclude_images=EXCLUDE_IMAGES,verbose=VERBOSE):
        print("Inventory full")

        print ("LET. HIM. COOK🥘")
# CLICK TARGET
# ============================================================
    if assist_click_target(kleur="rood", area="Bot_Area", bot_id=1, min_size=50, verbose=VERBOSE):
        print("Red found")
    else:
        print("Not found")

if __name__ == "__main__":
     main()
