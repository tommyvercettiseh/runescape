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
# VERBOSE LOGGING
# ============================================================
def log(msg: str, *, verbose: bool = False) -> None:
    if verbose:
        print(msg)


# ============================================================
# ANTIBAN OVERLAY
# ============================================================
def start_antiban_overlay(
    *,
    bot_id: int,
    bot_min: int = 60,
    bot_max: int = 70,
    rest_min: int = 10,
    rest_max: int = 15,
    verbose: bool = False,
) -> None:
    overlay_script = ROOT / "tools" / "overlay_launcher.py"

    if not overlay_script.is_file():
        log("Overlay script niet gevonden 🔴🖼️", verbose=verbose)
        return

    py = sys.executable if verbose else (shutil.which("pythonw") or sys.executable)

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
    log("Antiban overlay gestart 🟢🖼️", verbose=verbose)

    random_sleep()


# ============================================================
# RUN
# ============================================================
start_antiban_overlay(
    bot_id=BOT_ID,
    bot_min=60,
    bot_max=70,
    rest_min=10,
    rest_max=15,
    verbose=VERBOSE
)

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
else:
    print("Not skilling 🔴")
# ============================================================