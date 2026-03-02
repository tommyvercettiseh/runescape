# ============================================================
# HANDLER: Logout
# ============================================================

from __future__ import annotations

import time

from core.click_image import click_image
from vision.image_detection import detect_image
from helpers.random_sleep import sleep_custom
from core.move_to_area import move_to_area
from core.ai_cursor import click
from core.ansi import ANSIx

LOGIN_SCREEN = "Login_Screen_World.png"
LOGIN_AREA = "Bot_Area_Full"


def _clicked(img: str, area: str, bot_id: int, *, verbose: bool) -> bool:
    """
    Click image silently; only print when we actually clicked.
    """
    ok = click_image(img, area, bot_id=bot_id, verbose=False)
    if ok and verbose:
        print(ANSIx.ok(f"✅ Clicked | {img} in {area} | bot {bot_id}"))
    return bool(ok)


def _is_logged_out(bot_id: int) -> bool:
    """
    Silent check: are we on login screen?
    """
    return bool(detect_image(LOGIN_SCREEN, LOGIN_AREA, bot_id=bot_id, verbose=False))


def logout(bot_id: int = 1, timeout: float = 15, verbose: bool = False) -> bool:
    start = time.time()

    # Already logged out?
    if _is_logged_out(bot_id):
        verbose and print(ANSIx.ok("🚪 Already logged out"))
        return True

    verbose and print(ANSIx.info(f"🚪 Logout started | bot {bot_id}"))

    # focus client
    move_to_area("Chat_Area", bot_id=bot_id)
    click()

    # order matters: try most likely first
    steps = [
        ("Logout_Door.png", "Buttons_Bottom"),
        ("Logout_Door_2.png", "Inventory_Area"),
        ("Logout_ClickHereToLogout.png", "Inventory_Area"),
        ("Logout_ClickHereToLogout2.png", "Inventory_Area"),
    ]

    while (time.time() - start) < float(timeout):

        # success check (silent)
        if _is_logged_out(bot_id):
            verbose and print(ANSIx.ok("🚪 Logout success"))
            return True

        clicked_any = False
        for img, area in steps:
            if _clicked(img, area, bot_id, verbose=verbose):
                clicked_any = True
                # after a click, give UI a moment and re-check quickly
                sleep_custom(0.35, 0.65)
                if _is_logged_out(bot_id):
                    verbose and print(ANSIx.ok("🚪 Logout success"))
                    return True

        # if we didn't click anything, don't spam; just slow-poll
        if not clicked_any:
            sleep_custom(0.45, 0.75)

    verbose and print(ANSIx.fail("🚪 Logout failed | timeout"))
    return False


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    print("Test logout...\n")

    ok = logout(bot_id=1, timeout=15, verbose=True)

    result = ANSIx.ok("✅ UITGELOGD") if ok else ANSIx.fail("❌ NIET UITGELOGD")
    print("\n📊 RESULT:", result)


# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.actions.logout