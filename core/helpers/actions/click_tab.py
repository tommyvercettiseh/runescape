# ============================================================
# HANDLER: Click Tab
# ============================================================

import os
import time

from helpers.random_sleep import sleep_custom
from vision.image_detection import detect_image
from core.click_image import click_image
from core.paths import IMAGES_DIR
from core.move_to_area import move_outside_area
from core.ansi import ANSIx


# =========================
# AREAS
# =========================
TOP = "Buttons_Top"
BOTTOM = "Buttons_Bottom"
CONFIRM_AREA = "Tab_Confirmation_Area"
MOVE_OUT_AREA = "Info_Area"
# =========================
# TABS
# =========================
TABS = {
    "fight":     {"emoji": "⚔️", "area": TOP},
    "skilling":  {"emoji": "📚", "area": TOP},
    "inventory": {"emoji": "🎒", "area": TOP},
    "equipment": {"emoji": "🧰", "area": TOP},
    "prayer":    {"emoji": "🙏", "area": TOP},
    "spellbook": {"emoji": "📜", "area": TOP},
    "friends":   {"emoji": "👥", "area": BOTTOM},
    "logout":    {"emoji": "🚪", "area": BOTTOM},
    "settings":  {"emoji": "⚙️", "area": BOTTOM},
    "music":     {"emoji": "🎵", "area": BOTTOM},
}


# =========================
# HELPERS
# =========================
def _find_image(name):
    for f in os.listdir(IMAGES_DIR):
        if f.lower() == name.lower():
            return f
    return None


def _label(key):
    s = str(key).strip()
    return s[:1].upper() + s[1:].lower()


def assist_click_tab(tab, bot_id=1, verbose=False, timeout=3.0):

    key = str(tab).strip().lower()
    cfg = TABS.get(key)

    if not cfg:
        if verbose:
            print(ANSIx.fail("Unknown tab"), "|", tab)
        return False

    emo = cfg["emoji"]
    area = cfg["area"]
    label = _label(key)

    confirm_img = _find_image(f"Tab_{label}_Confirm.png")
    target_img = _find_image(f"Tab_{label}.png")

    if not confirm_img or not target_img:
        if verbose:
            print(ANSIx.fail("Missing image"), "|", label)
        return False

    # Already open?
    if detect_image(confirm_img, CONFIRM_AREA, bot_id):
        if verbose:
            print(ANSIx.ok(f"{emo} {label} already open"))
        return True

    if verbose:
        print(ANSIx.info(f"{emo} Opening {label}"))

    if not click_image(target_img, area, bot_id):
        if verbose:
            print(ANSIx.fail(f"{emo} Target not found | {label}"))
        return False

    move_outside_area(MOVE_OUT_AREA, bot_id=bot_id)

    end = time.time() + timeout

    while time.time() < end:
        if detect_image(confirm_img, CONFIRM_AREA, bot_id):
            if verbose:
                print(ANSIx.ok(f"{emo} Confirmed | {label}"))
            return True
        sleep_custom(0.12, 0.28)

    if verbose:
        print(ANSIx.warn(f"{emo} No confirmation | {label}"))

    return False


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=== TAB TEST ===\n")
    assist_click_tab("inventory", bot_id=1, verbose=True)
    
# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.actions.click_tab