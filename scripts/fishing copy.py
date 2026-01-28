# ============================================================
# BOOTSTRAP (altijd eerst)
# ============================================================
from pathlib import Path
import sys
import os
import random

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# SETTINGS
# ============================================================
BOT_ID = int(os.getenv("BOT_ID", "1"))
SKILL = os.getenv("SKILL", "Fishing").strip()

TRACE = False
VERBOSE = False
DEBUG = False

# (drop config)
EXCLUDE_SLOTS = {1}
EXCLUDE_IMAGES = [
    "Item_SmallFishingNet.png",
    "Item_Feathers.png",
    "Item_FlyFishingRod.png",
]

# ============================================================
# AUTOLOAD ✅ (geen core/vision/states imports meer)
# ============================================================
from core.autoload import autoload
autoload(globals(), verbose=False)

# ============================================================
# MAIN
# ============================================================
def main():

    # CAN WE START?
    if not can_start(bot_id=BOT_ID, verbose=VERBOSE, trace=TRACE):
        return

    # ARE WE SKILLING?
    if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
        print("✅ Skilling")
        return

    # RANDOMIZATION 🎲
    if random.random() < 0.01:
        VERBOSE and print("Checking experience 📊")
        assist_check_experience(SKILL, bot_id=BOT_ID, verbose=VERBOSE)

    # INVENTORY FULL? => DROP (of space bij chat)
    if inventory_full(
        bot_id=BOT_ID,
        exclude_slots=EXCLUDE_SLOTS,
        exclude_images=EXCLUDE_IMAGES,
        verbose=VERBOSE,
    ):
        print("LET. HIM. COOK🥘")

        # zorg dat we echt op target/area zitten (bot_id=None was fout)
        if assist_target(
            kleur="rood",
            area="Bot_Area",
            bot_id=BOT_ID,
            min_size=100,
            max_passes=2,
            verbose=VERBOSE,
        ):
            chat_corner = detect_image(
                "Chat_Area_Corner.png",
                "Chat_Area",
                bot_id=BOT_ID,
                verbose=VERBOSE,
                timeout=8,
                interval=1.0,
            )

            if not chat_corner:
                print("⛔ Chat corner niet gevonden → droppen")
                drop_inventory(
                    bot_id=BOT_ID,
                    exclude_slots=EXCLUDE_SLOTS,
                    exclude_images=EXCLUDE_IMAGES,
                    trace=VERBOSE,
                    debug=VERBOSE,
                )
            else:
                press_key("space")
                return

    # LET'S FISH!
    if not assist_click_target(
        kleur="paars",
        area="Bot_Area",
        bot_id=BOT_ID,
        min_size=200,
        verbose=VERBOSE,
    ):
        click_image("Icon_Fishing.png", "Info_Area", BOT_ID)
        return

    sleep_custom(2.1, 3.2)
    print("✅ Target found")
    return


if __name__ == "__main__":
    main()
