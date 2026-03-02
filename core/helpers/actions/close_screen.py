# ============================================================
# HANDLER: Close Screen
# ============================================================

import random

from core.click_image import click_image
from vision.image_detection import detect_image
from core.ansi import ANSIx
from helpers.random_sleep import sleep_custom
from ai_keyboard import press_key


IMAGE = "Close_Screen_X.png"
AREA = "Bot_Area"


def close_screen(bot_id=1, verbose=False):

    # open?
    if not detect_image(IMAGE, AREA, bot_id):
        if verbose:
            print(ANSIx.ok("🪟 No screen open"))
        return True

    use_click = random.random() < 0.5

    if use_click:
        if verbose:
            print(ANSIx.info("🪟 Closing via click"))
        ok = click_image(IMAGE, AREA, bot_id)
        sleep_custom(0.12, 0.25)
    else:
        if verbose:
            print(ANSIx.info("🪟 Closing via ESC"))
        press_key("esc")
        sleep_custom(1.51, 3.23)

        # fallback: ESC faalde
        ok = not detect_image(IMAGE, AREA, bot_id)
        if not ok:
            if verbose:
                print(ANSIx.warn("🪟 ESC failed, fallback click"))
            ok = click_image(IMAGE, AREA, bot_id)
            sleep_custom(0.12, 0.25)

    # endcheck
    closed = not detect_image(IMAGE, AREA, bot_id)

    if verbose:
        print(ANSIx.ok("🪟  Closed") if closed else ANSIx.fail("🪟  Close failed"))

    return closed


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("Test _close_screen...\n")
    result = close_screen(bot_id=1, verbose=True)
    print("\nRESULT:", ANSIx.ok("SUCCESS") if result else ANSIx.fail("FAILED"))


# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.actions.close_screen