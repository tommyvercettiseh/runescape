# ============================================================
# BOOTSTRAP 📂
# ============================================================
from pathlib import Path
import sys
import os
import random

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# SETTINGS ⚙️
# ============================================================
BOT_ID = int(os.getenv("BOT_ID", "1"))
SKILL = os.getenv("SKILL", "Fishing").strip()

TRACE = True
VERBOSE = True
DEBUG = False

# ============================================================
EXCLUDE_SLOTS = {1}

EXCLUDE_IMAGES = [
    "Item_RingMould.png"
]

SKILL               = "Crafting"

# ============================================================
# AUTOLOAD 🧠 
# ============================================================
from core.autoload import autoload
autoload(globals(), verbose=True, force_reload=True)

# ============================================================
# START 🧱
# ============================================================
def main():

# INVENTORY CHECK
# ============================================================
    game_on_button(bot_id=BOT_ID)
    assist_click_tab("Inventory", bot_id=BOT_ID, verbose=VERBOSE)
    assist_close_screen(bot_id=BOT_ID, verbose=VERBOSE)
# CAN WE START? 
# ============================================================
    if not can_start(bot_id=BOT_ID, verbose=VERBOSE, trace=TRACE):
        return

# ARE WE SKILLING? 
# ============================================================
    if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
        return
    
# ============================
# RANDOMIZATION 🎲
# ============================
    if random.random() < 0.01:
        VERBOSE and print("Checking experience 📊")
        assist_check_experience(SKILL, bot_id=BOT_ID, verbose=VERBOSE)

    # ============================================================
    # PRODUCT AUTO-DETECT 🧠
    # ============================================================
    product = None

    for product in ("Ring", "Necklace"):
        if detect_image(f"Item_{product}_Mould.png", "Inventory_Area", bot_id=BOT_ID, verbose=False):
            break
    else:
        VERBOSE and print("❌ Geen mould gevonden → stop")
        return

    IMAGE_TO_USE   = "Item_Gold_Bar.png"
    CONTINUE_IMAGE = f"Continue_Gold_{product}.png"

    # 👇 HIER — meteen erna
    VERBOSE and print(f"🧠 Product auto-detect → {product}")
    VERBOSE and print(f"📦 Continue image     → {CONTINUE_IMAGE}")

    # ============================================================

# IS OUR INVENTORY EMPTY? READY TO GO?
# ============================================================
    if not detect_image(IMAGE_TO_USE, "Inventory_Area", bot_id=BOT_ID, verbose=VERBOSE):

        if assist_banking(bot_id=BOT_ID, timeout_s=10):
            sleep_custom(0.1241, 1.1811)

            if deposit_inventory(bot_id=BOT_ID):
                sleep_custom(0.1241, 1.1811)

                if click_image(IMAGE_TO_USE, "Bot_Area", bot_id=BOT_ID, verbose=VERBOSE):
                    print(f"{IMAGE_TO_USE} found")
                    sleep_custom(1.1241, 1.7811)
                    assist_close_screen(bot_id=BOT_ID, verbose=VERBOSE)
                    sleep_custom(1.1241, 2.1811)
                else:
                    assist_click_exclude(bot_id=1, verbose=VERBOSE)
                    print("click_image failed -> exclude")
                    return


    # ✅ HIERNA gaat ie altijd verder (ook na assist_close_screen)
    assist_close_screen(bot_id=BOT_ID, verbose=VERBOSE)
    if assist_target(kleur="paars", area="Bot_Area", bot_id=BOT_ID, min_size=100, max_passes=2, verbose=VERBOSE):
        if detect_image(CONTINUE_IMAGE, "Bot_Area", bot_id=BOT_ID, verbose=VERBOSE, timeout=5, interval=0.5):
            if click_image(CONTINUE_IMAGE, "Bot_Area", bot_id=BOT_ID, verbose=VERBOSE):
                return


if __name__ == "__main__":
     main()
