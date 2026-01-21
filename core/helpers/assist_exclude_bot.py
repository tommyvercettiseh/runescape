import sys
from pathlib import Path
from datetime import datetime

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
# SCREENSHOT HELPER
# ============================================================
def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def log_area_screenshot(*, bot_id: int, area: str, label: str = "shot") -> str | None:
    out_dir = ROOT / "logs" / "screens"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{label}_bot{bot_id}_{area}_{_stamp()}.png"

    try:
        from PIL import ImageGrab  # type: ignore
        from core.bot_offsets import load_areas, apply_offset  # type: ignore

        areas = load_areas(None)
        if area not in areas:
            print(f"📸 Geen screenshot: area '{area}' niet gevonden in areas.json")
            return None

        coords = areas[area]

        # ✅ Coerce naar list [x1,y1,x2,y2]
        if isinstance(coords, tuple):
            coords = list(coords)
        elif isinstance(coords, list):
            coords = coords[:]  # kopie
        else:
            coords = list(coords)

        if len(coords) != 4:
            print(f"📸 Geen screenshot: area '{area}' heeft geen 4 coords: {coords}")
            return None

        coords = apply_offset(coords, bot_id=bot_id)

        x1, y1, x2, y2 = map(int, coords)
        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        img.save(out_path)

        print(f"📸 Screenshot opgeslagen: {out_path}")
        return str(out_path)

    except Exception as e:
        print(f"📸 Screenshot faalde ({type(e).__name__}): {e}")
        return None



# ============================================================
# ASSIST CLICK EXCLUDE
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
        print("🚫 Exclude gevonden → screenshot + klikken")

    # ✅ Screenshot vóór click (bot_id + Bot_Area_Full)
    log_area_screenshot(bot_id=bot_id, area="Bot_Area_Full", label="exclude_before")

    # 2) Eén klik, verder niks
    if click_image(target_img, area, bot_id, verbose=True):
        sleep_custom(1.1, 2.2)
        if not should_play(bot_id, verbose=False):
            if verbose:
                print("🚫 Exclude geklikt, bot is nu uitgesloten")

    return True


# ============================================================
# TEST
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
