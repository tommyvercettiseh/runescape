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
from helpers.random_sleep import random_sleep, sleep_custom

# ============================================================
# ASSIST LOGIN 🔐
# ============================================================
def assist_login(*, bot_id=1, timeout=20, verbose=False):
    start = time()

    LOGGED_IN_IMG = "xp.png"
    LOGGED_IN_AREA = "Info_Area"

    # 🔍 Al ingelogd?
    if detect_image(LOGGED_IN_IMG, LOGGED_IN_AREA, bot_id=bot_id, verbose=False):
        verbose and print("✅  🔐  Al ingelogd")
        return True

    verbose and print(f"⏳  🔐  Inloggen gestart     | bot {bot_id}")

    # 🔁 Login loop
    while time() - start < timeout:
        if detect_image(LOGGED_IN_IMG, LOGGED_IN_AREA, bot_id=bot_id, verbose=False):
            verbose and print("✅  🔐  Inloggen gelukt")
            return True

        # Play / OK varianten (veilig herhaalbaar)
        click_image("Ok.png", "Bot_Area_Full", bot_id, verbose=False)
        click_image("Login_Screen_Play_Now.png", "Bot_Area", bot_id, verbose=False)
        click_image("Login_Screen_Play_Now_Red.png", "Bot_Area_Full", bot_id, verbose=False)
        click_image("Login_Screen_Play_Now.png", "Bot_Area_Full", bot_id, verbose=False)

        sleep_custom(1.12, 3.00)

    verbose and print("⚠️  🔐  Inloggen mislukt     | timeout")
    return False


# ============================================================
# TEST 🧪
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1

    print("🧪  Test assist_login\n")

    ok = assist_login(
        bot_id=BOT_ID,
        timeout=15,
        verbose=True,
    )

    print("\n📊  RESULTAAT:", "✅  INGELOGD" if ok else "❌  NIET INGELOGD")
