import sys
from pathlib import Path
import random
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from core.click_image import click_image
from vision.image_detection import detect_image
from helpers.random_sleep import random_sleep

# ============================================================
# ASSIST BANKING
# ============================================================
# ============================================================
# ASSIST BANKING
# ============================================================
def assist_search(
    bot_id=1,
    verbose=True,
    timeout_s=6,
    poll_interval_s=2,
    attempts=2,
):
    TARGET_IMG = "Cyaan.png"
    AREA = "Bot_Area"

    found = detect_image(TARGET_IMG, AREA, bot_id, verbose=True)

    if verbose:
        print(f"🧪 Detect {TARGET_IMG} in {AREA} (bot {bot_id}) -> {found}")

    if found:
        if verbose:
            print("🟦 Cyaan zichtbaar ✅")
        return True
    else:
        if verbose:
            print("🟦 Cyaan NIET zichtbaar ❌")
        return False

assist_search(bot_id=1, verbose=True)