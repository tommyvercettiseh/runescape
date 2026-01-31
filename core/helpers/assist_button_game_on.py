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
from core.helpers.assist_target import assist_target
# ============================================================
# ASSIST BANKING
# ============================================================
def game_on_button(
    bot_id=1,
    verbose=True,
):
    
    IMAGE_SELECTED = "Tab_Chat_Game_On.png"
    IMAGE_NOT_SELECTED = "Tab_Chat_Game_Off.png"
    AREA = "Chat_Buttons"

    # 🔍 Bank al open?
    if not detect_image(IMAGE_SELECTED, AREA, bot_id, verbose=False):
        if verbose:
            print("✅ Game On Button")
            click_image(IMAGE_NOT_SELECTED, AREA, bot_id, verbose=False)

# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":
    BOT_ID = 1
    print("🧪 Test assist_banking")

    # voorbeeld: max 6 seconden wachten
    result = game_on_button(bot_id=BOT_ID)

    print("RESULT:", result)
