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
# AUTOLOAD (voorkeur) + FALLBACK IMPORTS
# ============================================================
_LOADED = False

try:
    # straks jouw main loader
    from core.autoload import autoload  # type: ignore
    autoload(globals(), verbose=False)  # inject alles in dit script (globals)
    _LOADED = True
except Exception:
    _LOADED = False

if not _LOADED:
    # fallback: werkt nu al, ook zonder loader
    from core.helpers.assist_login import assist_login
    from core.helpers.assist_logout import assist_logout
    from core.helpers.assist_click_target import assist_click_target
    from core.helpers.assist_click_tab import assist_click_tab
    from core.helpers.assist_check_experience import assist_check_experience
    from core.move_to_area import move_in_area

    from states.should_play_status import should_play
    from states.skilling_status import is_skilling
    from states.hp_status import enough_HP

    from helpers.random_sleep import sleep_custom


# ============================================================
# MAIN
# ============================================================
def main():
    # ============================
    # LOGIN / LOGOUT
    # ============================
    play = should_play(bot_id=BOT_ID, verbose=VERBOSE)
    if play:
        assist_login(bot_id=BOT_ID, verbose=VERBOSE)
        VERBOSE and print("Logged in ✅")
    else:
        assist_logout(bot_id=BOT_ID, verbose=VERBOSE)
        VERBOSE and print("Logged out ✅")
        return

    # ============================
    # SKILLING CHECK 🚦
    # ============================
    if is_skilling(bot_id=BOT_ID, verbose=VERBOSE):
        print("Skilling 🟢")
        return
    print("Not skilling 🔴")

    # ============================
    # TAB + SOMS EXP CHECK
    # ============================
    assist_click_tab("Inventory", bot_id=BOT_ID, verbose=VERBOSE)

    if random.random() < 0.01:
        VERBOSE and print("Checking experience 📊")
        assist_check_experience(SKILL, bot_id=BOT_ID, verbose=VERBOSE)

    # ============================
    # HP CHECK (altijd slim vóór actie)
    # ============================
    if not enough_HP(bot_id=BOT_ID, verbose=VERBOSE):
        return

    # ============================
    # CLICK TARGET
    # ============================
    move_in_area("Bot_Area", bot_id=BOT_ID, verbose=VERBOSE)
    sleep_custom(0.1, 1.2)

    clicked = assist_click_target(
        kleur="paars",
        area="Bot_Area",
        bot_id=BOT_ID,
        speed_pct=100,
        mode="random",
        verbose=VERBOSE,
        min_size=150,
        pick_strategy="nearest",
    )
    if clicked:
        return


if __name__ == "__main__":
    main()
