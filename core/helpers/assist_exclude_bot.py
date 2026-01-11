import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from helpers.random_sleep import sleep_custom
from core.click_image import click_image
from vision.image_detection import detect_image
from states.should_play_status import should_play

# ============================================================
# ASSIST CLICK EXCLUDE
# WAT: Klikt de Antiban exclude (paars) als deze zichtbaar is.
# WAAROM: Target uitsluiten zonder vervolglogica of aannames.
# ============================================================

def assist_click_exclude(
    *,
    target_img="Antiban_Exclude.png",
    area="Antiban_Area",
    bot_id=1,
    verbose=True,
) -> bool:
    # 1) Detecteren
    if not detect_image(target_img, area, bot_id=bot_id, verbose=False):
        if verbose:
            print("🚫 Exclude niet gevonden")
        return False

    if verbose:
        print("🚫 Exclude gevonden → klikken")

    # 2) Eén klik, verder niks
    if click_image(target_img, area, bot_id, verbose=True):
        sleep_custom(1.1, 2.2)
        if not should_play(bot_id, verbose=False):
            if verbose:
                print("🚫 Exclude geklikt, bot is nu uitgesloten")


    return True


# ============================================================
# TEST
# WAT: Snelle lokale test-run.
# WAAROM: Checken of detect + click werkt.
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    ok = assist_click_exclude(
        target_img="Antiban_Exclude.png",
        area="Antiban_Area",
        bot_id=BOT_ID,
        verbose=True,
    )
    print("RESULT:", ok)
