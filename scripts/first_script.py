
# ============================================================
# BOOTSTRAP (altijd eerst)
# ============================================================
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================

import time
from pathlib import Path
from vision.colour_detection import detect_colour
from vision.image_detection import detect_image
from core.click_image import click_image
from core.helpers.assist_login import assist_login

# ============================================================
# RUN
# ============================================================

VERBOSE = True

BOT_ID = 1

assist_login(bot_id=BOT_ID, timeout=15.0, verbose=VERBOSE)

if detect_image("XP.png", "Info_Area", bot_id=BOT_ID, verbose="short"):
    print ("Image found")
else: 
    print ("Image not found")


if detect_colour("green", "Skilling_Area", 3, bot_id=1, verbose=True):
    print ("Skilling")
else:
    print ("Not Skilling")

assist_login(bot_id=BOT_ID, timeout=15.0, verbose=VERBOSE)
click_image("Cyaan.png", "Bot_Area", BOT_ID)

for attempt in range(2):
    if click_image("Cyaan.png", "Bot_Area", BOT_ID):
        break