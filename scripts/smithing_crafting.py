# ============================================================
# BOOTSTRAP (altijd eerst)
# ============================================================
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# SETTINGS
# ============================================================
VERBOSE = False
BOT_ID = 1

# ============================================================
# IMPORTS (na bootstrap)
# ============================================================
import subprocess
import shutil
from core.ocr import ocr_text
from core.helpers.assist_login import assist_login
from core.helpers.assist_logout import assist_logout
from states.should_play_status import should_play
from states.skilling_status import is_skilling
from helpers.random_sleep import random_sleep

# ============================================================
# ASSIST LOGIN / LOGOUT
# ============================================================
Play = should_play(bot_id=BOT_ID, verbose=VERBOSE)
if Play:
    assist_login(bot_id=BOT_ID, verbose=VERBOSE)
    print("Logged in ✅")
else:
    assist_logout(bot_id=BOT_ID, verbose=VERBOSE)
    print("Logged out ✅")
# ============================================================
# CHECK SKILLING STATUS
# ============================================================
if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
    print("Skilling 🟢")
    sys.exit()
else:
    print("Not skilling 🔴")
# ============================================================

