# =========================
# ASSIST PLAYERS AROUND
# =========================
import sys
from pathlib import Path
import random
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.colour_detection import detect_colour
from send_screenshot import send_area_shot
from core.move_to_area import move_in_area
from core.ai_cursor import click
from ai_keyboard import type_text
from helpers.random_sleep import sleep_custom
from core.helpers import assist_click_tab

######################################################

def assist_world_hop(bot_id=1, verbose=True):
    move_in_area("Chat_Area", bot_id=bot_id, verbose=False, padding=3)
    click(button="left")
    sleep_custom(0.12, 0.25)
    type_text("q", enter=True)
    time.sleep(random.uniform(15, 35))
    assist_click_tab("Inventory", bot_id=BOT_ID, verbose=True)
    return True


if __name__ == "__main__":
    BOT_ID = 1
    while True:
        world_hop(bot_id=BOT_ID, verbose=True)
        time.sleep(0.3)
