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
import subprocess
import shutil

from vision.colour_detection import detect_colour
from vision.image_detection import detect_image

from core.click_image import click_image
from core.helpers.assist_login import assist_login
from core.helpers.assist_logout import assist_logout

from states.should_be_logged_in_status import should_be_logged_in
from states.skilling_status import is_skilling

from helpers.random_sleep import random_sleep

# ============================================================
# ANTIBAN OVERLAY
# ============================================================
# WAT: Start overlay_launcher.py als los proces voor deze bot.
# WAAROM: Overlay draait onafhankelijk van bot logic (Tk veilig).

def start_antiban_overlay(bot_id, bot_min=60, bot_max=70, rest_min=10, rest_max=15, verbose=False):
    overlay_script = ROOT / "tools" / "overlay_launcher.py"

    if not overlay_script.is_file():
        print("Overlay script niet gevonden 🔴🖼️")
        return

    # Bij verbose → console python (zodat errors zichtbaar zijn)
    # Anders → pythonw (stil)
    if verbose:
        py = sys.executable
    else:
        py = shutil.which("pythonw") or sys.executable

    args = [
        py,
        str(overlay_script),
        str(bot_id),
        str(bot_min),
        str(bot_max),
        str(rest_min),
        str(rest_max),
    ]

    if verbose:
        args.append("verbose")

    subprocess.Popen(args, close_fds=True)
    print("Antiban overlay gestart 🟢🖼️")

    random_sleep()
# ============================================================
# RUN
# ============================================================

VERBOSE = True
BOT_ID = 1

# 🔥 START ANTIBAN OVERLAY AUTOMATISCH BIJ BOT START
start_antiban_overlay(
    bot_id=BOT_ID,
    bot_min=60,
    bot_max=70,
    rest_min=10,
    rest_max=15,
    verbose=VERBOSE
)

# ============================================================
# BOT LOGIC
# ============================================================

if should_be_logged_in(bot_id=BOT_ID, verbose=VERBOSE):
    print("Should be logged in: {status} 🟢".format(status=should_be_logged_in(bot_id=BOT_ID, verbose=VERBOSE)    ))
else:
    print("Should be logged in: {status} 🔴".format(status=should_be_logged_in(bot_id=BOT_ID, verbose=VERBOSE)    ))

breakpoint()    

is_skilling_status = is_skilling(bot_id=BOT_ID, verbose=VERBOSE)
print(f"Skilling Status: {is_skilling_status}")


if detect_image("XP.png", "Info_Area", bot_id=BOT_ID, verbose="short"):
    print("Image found 🟢🖼️")
else:
    print("Image not found 🔴🖼️")

if detect_colour("green", "Skilling_Area", 3, bot_id=BOT_ID, verbose=True):
    print("Skilling 🟢")
else:
    print("Not skilling 🔴")

assist_login(bot_id=BOT_ID, timeout=15.0, verbose=VERBOSE)

click_image("Cyaan.png", "Bot_Area", BOT_ID)

for attempt in range(2):
    if click_image("Cyaan.png", "Bot_Area", BOT_ID):
        break

print("Klaar ✅")
