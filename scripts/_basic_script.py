# ============================================================
# BOOTSTRAP (altijd eerst)
# ============================================================
from pathlib import Path
import sys
from tabnanny import verbose



ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# SETTINGS
# ============================================================
VERBOSE = True
BOT_ID = 1

# ============================================================
# IMPORTS (na bootstrap)
# ============================================================
import subprocess
import shutil
from core.move_to_area import move_in_area
from core.helpers.assist_login import assist_login
from core.helpers.assist_logout import assist_logout
from states.should_play_status import should_play
from states.skilling_status import is_skilling
from helpers.random_sleep import random_sleep
from vision.colour_detection import detect_colour
from states.hp_status import enough_HP
from core.click_colour import click_colour  
# ============================================================
# VERBOSE LOGGING
# ============================================================
def log(msg: str, *, verbose: bool = False) -> None:
    if verbose:
        print(msg)

# ============================================================
# ASSIST LOGIN / LOGOUT
# ============================================================
# ============================================================
# CHECK SKILLING STATUS
# ============================================================

if detect_colour("cyaan", "Bot_Area", bot_id=1, verbose=True, min_size=400):
    click_colour("cyaan", "Bot_Area", bot_id=1, verbose=True, min_size=400,mode="deep_random",)