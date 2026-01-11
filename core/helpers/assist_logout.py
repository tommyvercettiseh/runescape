# ============================================================
# BOOTSTRAP
# WAT: Zet project-root (Runescape/) op sys.path.
# WAAROM: Zodat "from core...." altijd werkt, ook als je direct dit bestand runt.
# ============================================================
from __future__ import annotations

import sys
from pathlib import Path
from time import time

ROOT = Path(__file__).resolve().parents[2]  # <-- FIX: Runescape/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from core.click_image import click_image
from vision.image_detection import detect_image
from helpers.random_sleep import random_sleep
from core.move_to_area import move_to_area
from core.ai_cursor import click    
# ============================================================
# LOGOUT ASSIST
# WAT: Probeert uit te loggen en wacht tot login screen zichtbaar is.
# WAAROM: Stabiele logout flow met timeout + meerdere “logout routes”.
# ============================================================
def assist_logout(*, bot_id=1, timeout=15, verbose=False):
    start = time()

    LOGIN_SCREEN = "Login_Screen_World.png"
    LOGIN_AREA = "Bot_Area_Full"

    if detect_image(LOGIN_SCREEN, LOGIN_AREA, bot_id=bot_id, verbose=False):
        if verbose:
            print("Already logged out ✅")
        return True

    if verbose:
        print(f"🚪 Logging out (bot {bot_id})")

    move_to_area("Chat_Area", bot_id=bot_id)
    click()

    while time() - start < timeout:
        if detect_image(LOGIN_SCREEN, LOGIN_AREA, bot_id=bot_id, verbose=False):
            if verbose:
                print("✅ Uitloggen gelukt, login scherm zichtbaar")
            return True

        click_image("Logout_Door.png", "Buttons_Bottom", bot_id, verbose=False)
        random_sleep()

        click_image("Logout_Door_2.png", "Inventory_Area", bot_id, verbose=False)
        random_sleep()

        click_image("Logout_ClickHereToLogout.png", "Inventory_Area", bot_id, verbose=False)
        random_sleep()

    if verbose:
        print("⚠️ Uitloggen niet gelukt binnen timeout")
    return False


# ============================================================
# TEST
# WAT: Snelle lokale test-run.
# WAAROM: Checken of imports + logout flow werken.
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    ok = assist_logout(bot_id=BOT_ID, timeout=15, verbose=True)
    print(f"RESULT: {ok}")
