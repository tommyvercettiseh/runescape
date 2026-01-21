from __future__ import annotations

import sys
import time
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

from core.click_image import click_image
from core.click_colour import click_colour
from core.helpers.assist_click_target import assist_click_target

from vision.image_detection import detect_image
from vision.colour_detection import detect_colour

# ============================================================
# HELPERS
# ============================================================
SIZE = 400          # SIZE OF FIRE
TRACE = True
VERBOSE = True
IMAGE_TO_USE = "Item_All_Logs.png"

# ============================================================
# ASSIST FIREMAKING
# ============================================================
def assist_firemaking(bot_id=1, verbose=True):

    if verbose:
        print(f"🔥 Assist Firemaking. Start | Bot={bot_id}.")

    # ============================================================
    # STATE PRECHECK: Cyaan zichtbaar? Dan Use -> Target doen
    # ============================================================

    if detect_colour("cyaan", "Bot_Area", None, bot_id=bot_id, verbose=False, min_size=400, trace=TRACE):
        verbose and print("🟦 Cyaan Found. Use → Target.")

        # 1) Rightclick logs
        if not click_image(IMAGE_TO_USE, "Inventory_Area", bot_id=bot_id, button="right", verbose=verbose, timeout=3):
            verbose and print("⛔ Logs. Rightclick failed.")
            return False

        sleep_custom(0.10, 0.20)

        # 2) Click Use
        if not click_image("Use.png", "Bot_Area_Full", bot_id=bot_id, button="left", verbose=verbose, timeout=2):
            verbose and print("⛔ Use. Niet gevonden.")
            return False

        sleep_custom(0.05, 0.12)

        # 3) Click target cyaan
        if not click_colour(
            "cyaan",
            "Bot_Area",
            bot_id=bot_id,
            mode="deep_random",
            deep_erode_px=3,
            jitter_range=2,
            min_size=400,
            verbose=verbose,
            trace=TRACE,
        ):
            verbose and print("⛔ Target. Geen Cyaan klik.")
            return False

        # 4) Continue (optioneel, maar vaak handig)
        click_image("Firemaking_Continue.png", "Chat_Area", bot_id=bot_id, button="left", verbose=verbose, timeout=4)

        verbose and print("✅ Cyaan Flow Done.")
        return True
    return



    # anders: cyaan niet zichtbaar → ga gewoon verder met normale flow


        # Rightclick logs
        if not click_image(ITEM_LOGS, "Inventory_Area", bot_id=bot_id, button="right", verbose=verbose, timeout=2):
            verbose and print("⛔ Logs. Rightclick failed.")
            return False

        sleep_custom(0.12, 0.25)

        # Click Use
        if not click_image("Use.png", AREA_USE, bot_id=bot_id, button="left", verbose=verbose, timeout=2):
            verbose and print("⛔ Use. Niet gevonden.")
            return False

        # Click target (cyaan)
        if click_colour(
            "cyaan",
            AREA_TILE,
            bot_id=bot_id,
            mode="deep_random",
            deep_erode_px=3,
            jitter_range=2,
            min_size=SIZE,
            verbose=verbose,
        ):
            click_image("Firemaking_Continue.png", AREA_CHAT, bot_id=bot_id, button="left", verbose=verbose, timeout=3)

        verbose and print("✅ Assist Firemaking. Klaar (Cyaan State).")
        return True

    # ============================================================
    # NORMALE FLOW
    # ============================================================
    if verbose:
        print("🟧 Normal State. Start normale flow.")

    # Click fire tile (met timeout i.p.v. eerst detect + dan click)
    if not click_image(TILE_IMG, AREA_TILE, bot_id=bot_id, button="left", verbose=verbose, timeout=2):
        verbose and print("⏭️ Skip. Fire Tile niet gevonden/geklikt.")
        return False

    # Confirm tile in center (detect_image heeft geen timeout, dus wait_until wrapper)
    confirmed = wait_until(
        lambda: detect_image(TILE_IMG, AREA_TILE_CONFIRM, bot_id=bot_id, verbose=False),
        timeout=5,
        interval=0.5,
    )
    if not confirmed:
        verbose and print("❌ Timeout. Geen confirm binnen 5s.")
        return False

    verbose and print("🔥 Confirm. OK.")

    # Tinderbox
    if not click_image(ITEM_TINDER, "Inventory_Area", bot_id=bot_id, button="left", verbose=verbose, timeout=3):
        verbose and print("⛔ Tinderbox. Niet gevonden/geklikt.")
        return False

    # Logs
    if not click_image(ITEM_LOGS, "Inventory_Area", bot_id=bot_id, button="left", verbose=verbose, timeout=3):
        verbose and print("⛔ Logs. Niet gevonden/geklikt.")
        return False

    # Wacht op cyaan in center (detect_colour heeft ingebouwde timeout)
    hits = detect_colour(
        "cyaan",
        AREA_TILE_CONFIRM,
        percentage=3,
        bot_id=bot_id,
        verbose=False,
        min_size=SIZE,
        timeout=20,
        interval=0.5,
    )

    if not hits:
        verbose and print("❌ Timeout. Geen Cyaan binnen 20s.")
        return False

    verbose and print("🟦 Cyaan. Gevonden. Use -> Target.")

    # Rightclick logs
    if not click_image(ITEM_LOGS, "Inventory_Area", bot_id=bot_id, button="right", verbose=verbose, timeout=3):
        verbose and print("⛔ Logs. Rightclick failed.")
        return False

    sleep_custom(0.12, 0.25)

    # Click Use
    if not click_image("Use.png", AREA_USE, bot_id=bot_id, button="left", verbose=verbose, timeout=3):
        verbose and print("⛔ Use. Niet gevonden/geklikt.")
        return False

    # Click target
    ok = assist_click_target(
        kleur="cyaan",
        area=AREA_TILE,
        bot_id=bot_id,
        speed_pct=250,
        mode="random",
        verbose=verbose,
        min_size=SIZE,
        pick_strategy="nearest",
    )
    if not ok:
        verbose and print("⛔ Target. Click failed.")
        return False

    # Continue
    click_image("Firemaking_Continue.png", AREA_CHAT, bot_id=bot_id, button="left", verbose=verbose, timeout=3)

