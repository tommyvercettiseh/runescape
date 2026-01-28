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
ITEM_IMAGE = os.getenv("ITEM_IMAGE", "Item_Willow_Logs.png").strip()

SKILL = "Strength"
VERBOSE = False

# ============================================================
# AUTOLOAD ✅ (geen core/vision/states imports meer)
# ============================================================
from core.autoload import autoload
autoload(globals(), verbose=False)

# ============================================================
# MAIN
# ============================================================
def main():
    # LOGIN / LOGOUT
    if should_play(bot_id=BOT_ID, verbose=VERBOSE):
        assist_login(bot_id=BOT_ID, verbose=VERBOSE)
        VERBOSE and print("Logged in ✅")
    else:
        assist_logout(bot_id=BOT_ID, verbose=VERBOSE)
        VERBOSE and print("Logged out ✅")
        return

    # SKILLING CHECK
    if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
        print("Skilling 🟢")
        return
    print("Not skilling 🔴")

    # HEALTH
    try:
        assist_health(bot_id=BOT_ID, verbose=VERBOSE)
    except Exception:
        pass

    # TAB
    assist_click_tab("Inventory", bot_id=BOT_ID, verbose=VERBOSE)

    # SOMS EXP CHECK
    if random.random() < 0.01:
        VERBOSE and print("Checking experience 📊")
        assist_check_experience(SKILL, bot_id=BOT_ID, verbose=VERBOSE)

    # HP CHECK
    if not enough_HP(bot_id=BOT_ID, verbose=VERBOSE):
        return

    # CLICK TARGET
    move_in_area("Bot_Area", bot_id=BOT_ID, verbose=VERBOSE)
    sleep_custom(0.1, 1.2)

    if assist_click_target(
        kleur="paars",
        area="Bot_Area",
        bot_id=BOT_ID,
        speed_pct=100,
        mode="random",
        verbose=VERBOSE,
        min_size=150,
        pick_strategy="nearest",
    ):
        return


if __name__ == "__main__":
    main()
