from __future__ import annotations

import sys
from pathlib import Path

# ============================================================
# BOOTSTRAP
# ============================================================
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from helpers.random_sleep import sleep_custom
from helpers.ops import wait_until

from core.click_image import click_image, click_random_image
from core.click_colour import click_colour
from core.helpers.assist_click_target import assist_click_target
from vision.image_detection import detect_image
from vision.colour_detection import detect_colour

# ============================================================
# SETTINGS
# ============================================================
BOT_ID = 1
SIZE = 400
TRACE = True
VERBOSE = True

IMAGE_TO_USE = "Item_All_Logs.png"
TILE = "Tile_Fire.png"

# ============================================================
# HELPERS
# ============================================================
def _cyaan_present(*, bot_id=1, timeout=2.5, interval=0.5):
    return detect_colour("cyaan", "Bot_Area", None, bot_id=bot_id, verbose=False, min_size=SIZE, trace=TRACE, timeout=timeout, interval=interval)

def _cyaan_flow(*, bot_id=1, verbose=True):
    """
    Doet de volledige Use -> Target -> Continue flow zodra cyaan zichtbaar is.
    Returnt True als flow succesvol is afgerond, anders False.
    """
    if not _cyaan_present(bot_id=bot_id, timeout=2.5, interval=0.5):
        return False

    verbose and print("🟦 Cyaan Found. Use → Target.")

    if not click_random_image(IMAGE_TO_USE, "Inventory_Area", bot_id=bot_id, button="right", verbose=verbose):
        verbose and print("⛔ Logs. Rightclick failed.")
        return False

    sleep_custom(0.10, 0.20)

    if not click_image("Use.png", "Bot_Area_Full", bot_id=bot_id, button="left", verbose=verbose):
        verbose and print("⛔ Use. Niet gevonden.")
        return False

    sleep_custom(0.05, 0.12)

    if not click_colour("cyaan", "Bot_Area", bot_id=bot_id, mode="deep_random", deep_erode_px=3, jitter_range=2, min_size=SIZE, verbose=verbose, trace=TRACE):
        verbose and print("⛔ Target. Geen Cyaan klik.")
        return False

    sleep_custom(1.05, 1.12)

    if not detect_image("Firemaking_Continue.png", "Chat_Area", bot_id=bot_id, verbose=VERBOSE, timeout=3, interval=1.0):
        verbose and print("⛔ Continue. Niet gevonden binnen 5s.")
        return False

    sleep_custom(1.05, 2.12)
    click_image("Firemaking_Continue.png", "Chat_Area", bot_id=bot_id, button="left", verbose=VERBOSE)
    verbose and print("✅ Cyaan Flow Done.")
    return True

# ============================================================
# ASSIST FIREMAKING
# ============================================================
def assist_firemaking(bot_id=1, verbose=True):
    verbose and print(f"🔥 Assist Firemaking. Start | Bot={bot_id}.")

    # ============================================================
    # 1) HARD PRECHECK: als cyaan er is, meteen cyaan-flow (betrouwbaarder dan 1 snelle check)
    # ============================================================
    if _cyaan_present(bot_id=bot_id, timeout=2.5, interval=0.5):
        return _cyaan_flow(bot_id=bot_id, verbose=verbose)

    # ============================================================
    # 2) TILE CHECK: tile moet bestaan, anders eerst nog 1x cyaan rescue
    # ============================================================
    if not detect_image(TILE, "Bot_Area", bot_id=bot_id, verbose=VERBOSE, timeout=3, interval=1.0):
        if _cyaan_present(bot_id=bot_id, timeout=2.5, interval=0.5):
            verbose and print("🛟 Tile not found, but Cyaan found -> Cyaan Flow")
            return _cyaan_flow(bot_id=bot_id, verbose=verbose)
        verbose and print("⛔ Tile not found")
        return False

    # Tile klik (positioneer naar center)
    if click_image(TILE, "Bot_Area", bot_id=bot_id, button="left", verbose=VERBOSE):
        detect_image(TILE, "Bot_Area_Center", bot_id=bot_id, verbose=VERBOSE, timeout=5, interval=1.0)
        verbose and print("🟢 Tile found! Let's make fire!")

    # ============================================================
    # 3) TILE FLOW: wacht tot tile in center zichtbaar is
    # ============================================================
    if detect_image(TILE, "Bot_Area", bot_id=bot_id, verbose=VERBOSE, timeout=3, interval=1.0):
        verbose and print("🔥 Tile gevonden. Klik tile.")
        sleep_custom(0.15, 0.30)
        if not detect_image(TILE, "Bot_Area_Center", bot_id=bot_id, verbose=VERBOSE, timeout=8, interval=0.25):
            verbose and print("⛔ Tile. Niet zichtbaar in center.")
            return False
        verbose and print("✅ Tile in center zichtbaar.")

    # ============================================================
    # 4) USE: Tinderbox -> Logs -> wacht op Cyaan -> doe cyaan flow
    # ============================================================
    if click_image("Item_Tinderbox.png", "Inventory_Area", bot_id=bot_id, button="left", verbose=VERBOSE):
        if click_random_image(IMAGE_TO_USE, "Inventory_Area", bot_id=bot_id, verbose=verbose):
            if _cyaan_present(bot_id=bot_id, timeout=25, interval=1.0):
                verbose and print("🟦 Cyaan Found na Tinderbox → Logs.")
                return _cyaan_flow(bot_id=bot_id, verbose=verbose)

    verbose and print("⛔ Tinderbox/Logs/Cyaan flow failed.")
    return False

# ============================================================
# MAIN TEST
# ============================================================
if __name__ == "__main__":
    print("🧪 Firemaking assist test start")
    result = assist_firemaking(bot_id=1, verbose=True)
    print(f"🧪 Firemaking assist result: {result}")
