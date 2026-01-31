from __future__ import annotations

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
        from PIL import ImageGrab
        from core.bot_offsets import load_areas, apply_offset

        areas = load_areas(None)
        if area not in areas:
            print(f"📸 area '{area}' niet gevonden")
            return None

        coords = list(areas[area])
        coords = apply_offset(coords, bot_id=bot_id)

        x1, y1, x2, y2 = map(int, coords)
        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        img.save(out_path)

        print(f"📸 screenshot: {out_path}")
        return str(out_path)

    except Exception as e:
        print(f"📸 screenshot faalde ({type(e).__name__}): {e}")
        return None


# ============================================================
# ✅ OFFICIËLE NAAM
# ============================================================
def assist_click_exclude(
    *,
    target_img="Antiban_Exclude.png",
    area="Antiban_Area",
    bot_id=1,
    verbose=True,
) -> bool:
    # 1) detect
    if not detect_image(target_img, area, bot_id=bot_id, verbose=verbose):
        verbose and print("🚫 exclude niet gevonden")
        return False

    verbose and print("🚫 exclude gevonden → screenshot + klik poging")

    # 2) bewijs screenshot
    log_area_screenshot(bot_id=bot_id, area="Bot_Area_Full", label="exclude_before")

    # 3) klik
    if not click_image(target_img, area, bot_id, verbose=verbose):
        verbose and print("🚫 exclude gevonden, maar click_image faalde")
        return False

    sleep_custom(1.1, 2.2)

    # 4) validatie (✅ keyword-only)
    if not should_play(bot_id=bot_id, verbose=False):
        verbose and print("🚫 exclude geklikt, bot is nu uitgesloten")
    else:
        verbose and print("⚠️ exclude geklikt, maar bot speelt nog")

    return True


# ============================================================
# 🔁 BACKWARDS COMPAT NAMES
# ============================================================
def assist_exclude_bot(
    *,
    target_img="Antiban_Exclude.png",
    area="Antiban_Area",
    bot_id=1,
    verbose=True,
) -> bool:
    return assist_click_exclude(
        target_img=target_img,
        area=area,
        bot_id=bot_id,
        verbose=verbose,
    )


def assist_click_exclude_bot(
    *,
    target_img="Antiban_Exclude.png",
    area="Antiban_Area",
    bot_id=1,
    verbose=True,
) -> bool:
    return assist_click_exclude(
        target_img=target_img,
        area=area,
        bot_id=bot_id,
        verbose=verbose,
    )


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    print("RESULT:", assist_click_exclude(bot_id=1, verbose=True))
