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

CONTINUE_IMAGE =    "Continue_Gold_Ring.png"

# ============================================================
# AUTOLOAD 🧠 
# ============================================================
from core.autoload import autoload
autoload(globals(), verbose=VERBOSE)

# ============================================================
# START 🧱
# ============================================================
def main():
        assist_random_event(bot_id=BOT_ID,area="Bot_Area",verbose=True,package="core.helpers.random")

if __name__ == "__main__":
     main()
