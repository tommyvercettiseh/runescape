import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from core.click_image import click_image
from vision.image_detection import detect_image


# ============================================================
# ASSIST CLICK TARGET
# WAT: Detecteert jouw paarse target en klikt 1x als hij zichtbaar is.
# WAAROM: Target-activering is altijd hetzelfde; vervolglogica hoort elders.
# ============================================================
def assist_click_target(
    *,
    target_img="Paars.png",
    area="Bot_Area",
    bot_id=1,
    verbose=True,
) -> bool:
    # 1) Detecteren (geen retries, geen klikspam)
    if not detect_image(target_img, area, bot_id=bot_id, verbose=False):
        if verbose:
            print("🟣 Target niet gevonden ❌")
        return False

    if verbose:
        print("🟣 Target gevonden → klikken")

    # 2) Eén klik, verder niks
    click_image(target_img, area, bot_id, verbose=False)
    return True


# ============================================================
# TEST
# WAT: Snelle lokale test-run.
# WAAROM: Checken of detect + click werkt.
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    ok = assist_click_target(
        target_img="Paars.png",
        area="Bot_Area",
        bot_id=BOT_ID,
        verbose=True,
    )
    print("RESULT:", ok)
