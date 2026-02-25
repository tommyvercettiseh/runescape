import sys
import time
from pathlib import Path
import random

# ============================================================
# BOOTSTRAP 🚀
# ============================================================
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS 📥
# ============================================================
from core.click_image import click_image
from vision.image_detection import detect_image
from ai_keyboard import press_key
from helpers.random_sleep import random_sleep

# ============================================================
# CONFIG ⚙️
# ============================================================
IMAGE = "Close_Screen_X.png"
AREA = "Bot_Area"

# ============================================================
# ASSIST CLOSE SCREEN 🪟
# ============================================================
def assist_close_screen(bot_id=1, verbose=True):

    # 🔍 Is er iets open?
    if not detect_image(IMAGE, AREA, bot_id, verbose=False):
        verbose and print("✅  🪟  Geen scherm open")
        return True

    # 🎲 50/50 keuze: click of ESC
    use_click = random.random() < 0.5

    if use_click:
        verbose and print("⏳  🪟  Sluiten via click")
        click_image(IMAGE, AREA, bot_id, verbose=False)

    else:
        verbose and print("⏳  🪟  Sluiten via ESC")
        press_key("esc")
        time.sleep(random.triangular(1.51, 2.12, 3.23))

        # fallback: ESC faalde
        if detect_image(IMAGE, AREA, bot_id, verbose=False):
            verbose and print("⚠️  🪟  ESC faalde   → fallback click")
            click_image(IMAGE, AREA, bot_id, verbose=False)
        time.sleep(random.triangular(1.51, 2.12, 3.23))

    # 🔁 Eindcheck
    if not detect_image(IMAGE, AREA, bot_id, verbose=False):
        verbose and print("✅  🪟  Scherm gesloten")
        return True

    verbose and print("❌  🪟  Sluiten mislukt")
    return False


# ============================================================
# TEST 🧪
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    print("🧪  Test assist_close_screen\n")

    result = assist_close_screen(bot_id=BOT_ID, verbose=True)

    print("\n📊  RESULTAAT:", "✅  SUCCES" if result else "❌  GEFAALD")
