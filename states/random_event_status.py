# ============================================================
# BOOTSTRAP
# ============================================================
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from vision.colour_detection import detect_colour
from vision.image_detection import detect_image 
from helpers.random_sleep import sleep_custom
from send_screenshot import send_area_shot

BOT_ID = 1

# ============================================================
# HP STATUS
# ============================================================
def random_event(bot_id=BOT_ID, verbose=False):
    if detect_image("Notification_Random_Event.png", "Chat_Area", bot_id=BOT_ID, verbose=verbose):
        sleep_custom(0.12, 0.25)
        send_area_shot("Bot_Area_Full", "⚠️  Random Event!", bot_id=BOT_ID)
        if verbose: print("⚠️  Random Event detected!")
        return True
# ============================================================
# MAIN (standalone test)
# ============================================================

if __name__ == "__main__":
    BOT_ID = 1
    VERBOSE = True

    print("Random Event Found?:", random_event(bot_id=BOT_ID, verbose=VERBOSE))
