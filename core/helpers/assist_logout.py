# ============================================================
# BOOTSTRAP
# ============================================================
from __future__ import annotations

import sys
from pathlib import Path
from time import time, sleep

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.click_image import click_image
from vision.image_detection import detect_image


# ============================================================
# LOGOUT ASSIST
# ============================================================
def assist_logout(*, bot_id: int = 1, timeout: float = 15.0, verbose: bool = False) -> bool:
    start = time()

    if verbose:
        print(f"🚪 Logging out (bot {bot_id})")

    while time() - start < timeout:
        if detect_image("Login_Screen_World.png", "Bot_Area_Full", bot_id=bot_id, verbose="off"):
            if verbose:
                print("✅ Uitloggen gelukt, login scherm zichtbaar")
            return True

        if click_image("Logout_Door.png", "Buttons_Bottom", bot_id=bot_id, anchor="random", padding=2, verbose="off"):
            if verbose:
                print("🖱️ Logout knop aangeklikt")
            sleep(0.8)

        if click_image("Logout_ClickHereToLogout.png", "Inventory_Area", bot_id=bot_id, anchor="random", padding=2, verbose="off"):
            if verbose:
                print("🖱️ Logout bevestigd")
            sleep(0.8)

        sleep(0.3)

    if verbose:
        print("⚠️ Uitloggen niet gelukt binnen timeout")
    return False


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    ok = assist_logout(bot_id=BOT_ID, timeout=15.0, verbose=True)
    print(f"RESULT: {ok}")
