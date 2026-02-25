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
from core.ai_cursor import click
from core.move_to_area import move_in_area
from vision.colour_detection import detect_colour
from helpers.random_sleep import sleep_custom
from ai_keyboard import type_text
from send_screenshot import send_area_shot

# ============================================================
# CHECK: Nearby Players (cyan dots on minimap)
# ============================================================
def nearby_players(bot_id=1, verbose=False):
    if detect_colour("#00FFFF", "Map_Area", bot_id=bot_id):
        verbose and print("Other players around!🔴")
        move_in_area("Chat_Area", bot_id=bot_id, verbose=False, padding=3)
        click(button="left")
        sleep_custom(0.12, 0.25)
        send_area_shot("Bot_Area_Full", "⚠️ Other players nearby 👀", bot_id=bot_id)
        return True
    return False

if __name__ == "__main__":
    BOT_ID = 1
    VERBOSE = True

    print("🟦 Nearby players:", nearby_players(bot_id=BOT_ID, verbose=VERBOSE))
