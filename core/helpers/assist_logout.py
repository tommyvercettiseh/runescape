# ============================================================
# BOOTSTRAP 🚀
# ============================================================
from __future__ import annotations

import sys
from pathlib import Path
from time import time

ROOT = Path(__file__).resolve().parents[2]  # Runescape/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS 📥
# ============================================================
from core.click_image import click_image
from vision.image_detection import detect_image
from helpers.random_sleep import random_sleep
from core.move_to_area import move_to_area
from core.ai_cursor import click

# ============================================================
# ASSIST LOGOUT 🚪
# ============================================================
def assist_logout(*, bot_id=1, timeout=15, verbose=False):
    start = time()

    LOGIN_SCREEN = "Login_Screen_World.png"
    LOGIN_AREA = "Bot_Area_Full"

    # 🔍 Al uitgelogd?
    if detect_image(LOGIN_SCREEN, LOGIN_AREA, bot_id=bot_id, verbose=False):
        verbose and print("✅  🚪  Al uitgelogd")
        return True

    verbose and print(f"⏳  🚪  Uitloggen gestart    | bot {bot_id}")

    # Focus op client
    move_to_area("Chat_Area", bot_id=bot_id)
    click()

    # 🔁 Logout loop
    while time() - start < timeout:
        if detect_image(LOGIN_SCREEN, LOGIN_AREA, bot_id=bot_id, verbose=False):
            verbose and print("✅  🚪  Uitloggen gelukt     | login scherm zichtbaar")
            return True

        # Mogelijke logout routes
        click_image("Logout_Door.png", "Buttons_Bottom", bot_id, verbose=False)
        random_sleep()

        click_image("Logout_Door_2.png", "Inventory_Area", bot_id, verbose=False)
        random_sleep()

        click_image("Logout_ClickHereToLogout.png", "Inventory_Area", bot_id, verbose=False)
        random_sleep()

        click_image("Logout_ClickHereToLogout2.png", "Inventory_Area", bot_id, verbose=False)
        random_sleep()

    verbose and print("⚠️  🚪  Uitloggen mislukt    | timeout")
    return False


# ============================================================
# TEST 🧪
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1

    print("🧪  Test assist_logout\n")

    ok = assist_logout(
        bot_id=BOT_ID,
        timeout=15,
        verbose=True,
    )

    print("\n📊  RESULTAAT:", "✅  UITGELOGD" if ok else "❌  NIET UITGELOGD")
