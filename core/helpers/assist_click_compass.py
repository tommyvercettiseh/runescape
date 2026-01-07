import sys
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from core.click_image import click_image
from core.ai_cursor import click
from vision.image_detection import detect_image
from helpers.random_sleep import random_sleep
from core.move_to_area import move_in_area

# ============================================================
# ASSIST BANKING
# WAT: Opent de bank (als die nog niet open is).
# WAAROM: Betrouwbare bank-open flow met retries + 50/50 input variatie.
# ============================================================
from core.move_to_area import move_in_area
from core.ai_cursor import click
from core.click_image import click_image
from helpers.random_sleep import sleep_custom

DIRECTIONS = {
    "north": "Compass_North.png",
    "south": "Compass_South.png",
    "west":  "Compass_West.png",
    "east":  "Compass_East.png",
}

def assist_click_compass(direction, bot_id=1, verbose=True):
    d = str(direction).strip().lower()
    img = DIRECTIONS.get(d)

    if not img:
        if verbose:
            print(f"❌ Onbekende richting: {direction} (north/south/west/east)")
        return False

    # optioneel: eerst cursor “menselijk” naar kompas-area
    move_in_area("Info_Area", bot_id=bot_id, verbose=False, padding=3)
    click(button="right")  # context menu open (als dat in jouw UI zo werkt)
    sleep_custom(0.12, 0.25)

    # klik de gewenste optie
    ok = click_image(img, "Bot_Area", bot_id, verbose=False)
    if verbose:
        print(("✅" if ok else "❌") + f" richting: {d}")
    return ok
