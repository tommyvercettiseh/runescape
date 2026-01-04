import sys
from pathlib import Path
from time import sleep
import random
# ============================================================
# IMPORTS
# ============================================================
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.click_image import click_image
from vision.image_detection import detect_image
from ai_keyboard import press_key
from helpers.random_sleep import random_sleep

# ============================================================
# CONFIG
# ============================================================

IMAGE = "Close_Screen_X.png"
AREA = "Bot_Area"
# ============================================================

def assist_close_screen(bot_id=1, verbose=True):
    # als het niet open is: klaar
    if not detect_image(IMAGE, AREA, bot_id, verbose=False):
        if verbose:
            print("🪟  Niks open ✅")
        return True

    # 50/50 keuze
    use_click = random.random() < 0.5

    if use_click:
        if verbose:
            print("🎯  Close via click_image")
        click_image(IMAGE, AREA, bot_id, verbose=False)

    else:
        if verbose:
            print("⌨️  Close via ESC (50/50)")
        press_key("esc")
        random_sleep()

        # focus fail → nog open? dan 1x click fallback
        if detect_image(IMAGE, AREA, bot_id, verbose=False):
            if verbose:
                print("😵  ESC faalde, fallback click ✅")
            click_image(IMAGE, AREA, bot_id, verbose=False)
            random_sleep()

    # eindcheck
    if not detect_image(IMAGE, AREA, bot_id, verbose=False):
        if verbose:
            print("🪟  Gesloten ✅")
        return True

    if verbose:
        print("⚠️  Nog open")
    return False


# ============================================================

if __name__ == "__main__":
    BOT_ID = 1
    print("🧪  Test assist_close_screen")
    result = assist_close_screen(bot_id=BOT_ID, verbose=True)
    print("RESULT:", result)
