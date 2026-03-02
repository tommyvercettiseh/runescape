# ============================================================
# HANDLER: Exclude Bot
# ============================================================

from datetime import datetime
from pathlib import Path

from helpers.random_sleep import sleep_custom
from core.click_image import click_image
from vision.image_detection import detect_image
from core.ansi import ANSIx
from states.should_play_status import should_play

# ============================================================
# SCREENSHOT
# ============================================================

def _stamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def log_area_screenshot(bot_id=1, area="Bot_Area_Full", label="exclude"):

    from PIL import ImageGrab
    from core.bot_offsets import load_areas, apply_offset

    root = Path(__file__).resolve().parents[2]
    out_dir = root / "logs" / "screens"
    out_dir.mkdir(parents=True, exist_ok=True)

    areas = load_areas(None)
    if area not in areas:
        print(ANSIx.fail(f"📸 Area not found | {area}"))
        return None

    coords = apply_offset(list(areas[area]), bot_id=bot_id)
    x1, y1, x2, y2 = map(int, coords)

    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    path = out_dir / f"{label}_bot{bot_id}_{_stamp()}.png"
    img.save(path)

    print(ANSIx.info(f"📸 Screenshot saved"))
    return str(path)


# ============================================================
# MAIN HANDLER
# ============================================================

def assist_click_exclude(
    bot_id=1,
    target_img="Antiban_Exclude.png",
    area="Antiban_Area",
    verbose=False,
):

    if not detect_image(target_img, area, bot_id):
        if verbose:
            print(ANSIx.ok("🚫 Exclude not visible"))
        return False

    if verbose:
        print(ANSIx.warn("🚫 Exclude detected"))

    log_area_screenshot(bot_id=bot_id)

    if not click_image(target_img, area, bot_id):
        if verbose:
            print(ANSIx.fail("🚫 Click failed"))
        return False

    sleep_custom(1.1, 2.2)

    excluded = not should_play(bot_id=bot_id)

    if verbose:
        print(
            ANSIx.fail("🚫 Bot excluded")
            if excluded
            else ANSIx.warn("⚠️ Exclude clicked but still playing")
        )

    return True


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("Test exclude handler...\n")
    result = assist_click_exclude(bot_id=1, verbose=True)
    print("\nRESULT:", ANSIx.ok("SUCCESS") if result else ANSIx.fail("FAILED"))


# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.actions.exclude_bot