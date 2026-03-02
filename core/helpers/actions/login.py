# ============================================================
# HANDLER: Login
# ============================================================

import time

from core.click_image import click_image
from vision.image_detection import detect_image
from helpers.random_sleep import sleep_custom
from core.ansi import ANSIx


LOGGED_IN_IMG = "xp.png"
LOGGED_IN_AREA = "Info_Area"

CLICK_SEQUENCE = [
    ("Ok.png", "Bot_Area_Full"),
    ("Login_Screen_Play_Now.png", "Bot_Area"),
    ("Login_Screen_Play_Now_Red.png", "Bot_Area_Full"),
    ("Login_Screen_Play_Now.png", "Bot_Area_Full"),
]


def assist_login(bot_id=1, timeout=20, verbose=False):

    if detect_image(LOGGED_IN_IMG, LOGGED_IN_AREA, bot_id):
        if verbose:
            print(ANSIx.ok("🔐 Already logged in"))
        return True

    if verbose:
        print(ANSIx.info(f"🔐 Login started | bot {bot_id}"))

    end = time.time() + float(timeout)

    while time.time() < end:

        if detect_image(LOGGED_IN_IMG, LOGGED_IN_AREA, bot_id):
            if verbose:
                print(ANSIx.ok("🔐 Login success"))
            return True

        for img, area in CLICK_SEQUENCE:
            click_image(img, area, bot_id)

        sleep_custom(1.12, 3.00)

    if verbose:
        print(ANSIx.warn("🔐 Login failed | timeout"))

    return False


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    BOT_ID = 1

    print("🧪  Test assist_login\n")

    ok = assist_login(
        bot_id=BOT_ID,
        timeout=15,
        verbose=True,
    )

    status = ANSIx.ok("✅ INGELOGD") if ok else ANSIx.fail("❌ NIET INGELOGD")
    print("\n📊  RESULTAAT:", status)


# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.actions.login