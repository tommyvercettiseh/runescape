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

from vision.image_detection import detect_image

# ============================================================
# SETTINGS ⚙️
# ============================================================
BOT_ID = int(os.getenv("BOT_ID", "1"))

TRACE = False
VERBOSE = True
DEBUG = True

# ============================================================

# START 🧱
# ============================================================
def main():

    if not detect_image("Firemaking_Continue.png", "Chat_Area", bot_id=BOT_ID, verbose=VERBOSE, timeout=3, interval=1.0):
        print("No continue button, starting firemaking script...")

if __name__ == "__main__":
     main()
