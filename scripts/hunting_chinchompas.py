# ============================================================
# BOOTSTRAP 📂
# ============================================================
from pathlib import Path
import sys
import os
import random
import time
from time import time as now
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ============================================================
# SETTINGS ⚙️
# ============================================================
BOT_ID = int(os.getenv("BOT_ID", "1"))
TRACE = False
VERBOSE = False
DEBUG = False
# ============================================================
# AUTOLOAD 🧠 
# ============================================================

# Core functions
from core.helpers.assist_check_experience import assist_check_experience
from core.helpers.assist_click_tab import assist_click_tab
from core.helpers.assist_world_hop import assist_world_hop

from core.move_to_area import move_in_area
from core.click_image import click_image
from core.ai_cursor import click
from core.click_colour import click_colour
from core.ai_cursor_movement import random_mouse_movements
from send_screenshot import send_area_shot
from vision.colour_detection import detect_colour
from states.random_event_status import random_event
from ai_keyboard import type_random_phrase, type_text

# STATES
from states.nearby_players_status import nearby_players
from states.can_start_status import can_start

# ============================================================
# START 🧱
# ============================================================
def main():

    while True:
        if not can_start(bot_id=BOT_ID, verbose=VERBOSE, trace=TRACE):
            return
# ============================
# RANDOMIZATION 🎲
# ============================
        if random.random() < 0.03:
            VERBOSE and print("Checking experience 📊")
            assist_check_experience("Hunter", bot_id=BOT_ID, verbose=VERBOSE)

        if random_event(bot_id=BOT_ID, verbose=VERBOSE):
            time.sleep(random.triangular(20.51, 50.12, 32.23))

# ============================
# PLAYERS AROUND?
# ============================
        if nearby_players(bot_id=BOT_ID, verbose=VERBOSE):
            move_in_area("Chat_Area", bot_id=BOT_ID, verbose=False, padding=3)
            click(button="left")
            type_text("sup", "i'll hop", "hopping","i hop :)", "goodluck", "gl mate","kk","off i go :)","I hop","-.-", enter=True)
            send_area_shot("Bot_Area_Full", "⚠️ Other players nearby 👀", bot_id=BOT_ID)
            assist_world_hop(bot_id=BOT_ID, verbose=VERBOSE)
# ============================
        if click_image("Box_Trap_Text.png", "Bot_Area", bot_id=BOT_ID, verbose=VERBOSE):
            if random.random() < 0.8:
                random_mouse_movements(1, 5, "Bot_Area_Full", bot_id=BOT_ID, verbose=VERBOSE)
                move_in_area("Offscreen", bot_id=BOT_ID, verbose=VERBOSE)
            time.sleep(random.triangular(4.51, 18.12, 7.23))
            continue

        if click_image("Box_Trap_Dashes_Combi.png", "Bot_Area", bot_id=BOT_ID, verbose=VERBOSE):
            if random.random() < 0.8:
                move_in_area("Offscreen", bot_id=BOT_ID, verbose=VERBOSE)
            time.sleep(random.triangular(4.51, 18.12, 7.23))
            continue

        if click_colour("paars", "Bot_Area", bot_id=BOT_ID, mode="deep_random", deep_erode_px=8, jitter_range=0, min_size=50, verbose=VERBOSE):
            if random.random() < 0.8:
                move_in_area("Offscreen", bot_id=BOT_ID, verbose=VERBOSE)
            time.sleep(random.triangular(8.51, 18.12, 10.23))
            continue
                    
        if click_colour("rood", "Bot_Area", bot_id=BOT_ID, mode="deep_random", deep_erode_px=8, jitter_range=0, min_size=50, verbose=VERBOSE):
            if random.random() < 0.8:
                move_in_area("Offscreen", bot_id=BOT_ID, verbose=VERBOSE)
            time.sleep(random.triangular(8.51, 18.12, 10.23))
            continue

        if click_image("Box_Trap_Dashes.png", "Bot_Area", bot_id=BOT_ID, verbose=VERBOSE):
            assist_click_tab("Inventory", bot_id=BOT_ID, verbose=VERBOSE)
            time.sleep(random.triangular(2.511, 8.1234,10.54))

            if random.random() < 0.5:
                if click_image("Box_Trap_Inventory.png", "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE):
                    if random.random() < 0.67:
                        move_in_area("Offscreen", bot_id=BOT_ID, verbose=VERBOSE)
                    time.sleep(random.triangular(4.51, 18.12, 7.23))
                    continue

            else:
                if click_image("Box_Trap_Inventory.png", "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE, button="right"):
                    time.sleep(random.triangular(0.91, 1.12, 1.833))
                    if click_image("Box_Trap_Lay.png", "Bot_Area_Full", bot_id=BOT_ID, verbose=VERBOSE):
                        if random.random() < 0.81:
                            move_in_area("Offscreen", bot_id=BOT_ID, verbose=VERBOSE)

                        time.sleep(random.triangular(4.51, 18.12, 7.23))
                continue

if __name__ == "__main__":
     main()
