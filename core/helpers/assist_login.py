# ============================================================
# BOOTSTRAP
# WAT: Zet project-root (Runescape/) op sys.path.
# WAAROM: Zodat "from core...." altijd werkt, ook als je direct dit bestand runt.
# ============================================================
from __future__ import annotations

import sys
from pathlib import Path
from time import time

ROOT = Path(__file__).resolve().parents[2]  # Runescape/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from core.click_image import click_image
from vision.image_detection import detect_image
from helpers.random_sleep import random_sleep, sleep_custom


# ============================================================
# ASSIST LOGIN
# WAT: Probeert in te loggen en wacht tot "xp.png" zichtbaar is.
# WAAROM: Stabiele login flow met timeout + meerdere “play now” varianten.
# ============================================================
def assist_login(*, bot_id=1, timeout=20, verbose=False):
    start = time()

    LOGGED_IN_IMG = "xp.png"
    LOGGED_IN_AREA = "Info_Area"

    if detect_image(LOGGED_IN_IMG, LOGGED_IN_AREA, bot_id=bot_id, verbose=False):
        if verbose:
            print("Already logged in ✅")
        return True

    if verbose:
        print(f"🔐 Logging in (bot {bot_id})")

    while time() - start < timeout:
        if detect_image(LOGGED_IN_IMG, LOGGED_IN_AREA, bot_id=bot_id, verbose=False):
            if verbose:
                print("Logged in! ✅")
            return True

        click_image("Ok.png", "Bot_Area_Full", bot_id, verbose=False)

        click_image("Login_Screen_Play_Now.png", "Bot_Area", bot_id, verbose=False)

        click_image("Login_Screen_Play_Now_Red.png", "Bot_Area_Full", bot_id, verbose=False)

        click_image("Login_Screen_Play_Now.png", "Bot_Area_Full", bot_id, verbose=False)
        sleep_custom(1.124546,2.9992)

    if verbose:
        print("⚠️ Inloggen niet gelukt binnen timeout")
    return False


# ============================================================
# TEST
# WAT: Snelle lokale test-run.
# WAAROM: Checken of imports + login flow werken.
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    ok = assist_login(bot_id=BOT_ID, timeout=15, verbose=True)
    print(f"RESULT: {ok}")
