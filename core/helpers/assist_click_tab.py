from __future__ import annotations
import sys
from pathlib import Path
import time
import os

ROOT = Path(__file__).resolve().parents[2]  # Runescape/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from helpers.random_sleep import sleep_custom
from vision.image_detection import detect_image
from core.click_image import click_image
from core.paths import IMAGES_DIR
from core.move_to_area import move_outside_area

# =========================
# AREAS
# =========================
TOP = "Buttons_Top"
BOTTOM = "Buttons_Bottom"
CONFIRM_AREA = "Tab_Confirmation_Area"
MOVE_OUT_AREA = "Info_Area"

# =========================
# TABS PRESETS (alleen dit onderhouden)
# =========================
TABS = {
    "fight":     {"emoji": "⚔️", "target_area": TOP},
    "skilling":    {"emoji": "📚", "target_area": TOP},
    "inventory": {"emoji": "🎒", "target_area": TOP},
    "equipment": {"emoji": "🧰", "target_area": TOP},
    "prayer":    {"emoji": "🙏", "target_area": TOP},
    "spellbook": {"emoji": "📜", "target_area": TOP},

    "friends":   {"emoji": "👥", "target_area": BOTTOM},
    "logout":    {"emoji": "🚪", "target_area": BOTTOM},
    "settings":  {"emoji": "⚙️", "target_area": BOTTOM},
    "music":     {"emoji": "🎵", "target_area": BOTTOM},
}

# =========================
# IMAGE HELPERS
# =========================
def _find_image(name: str) -> str | None:
    want = name.lower()
    for f in os.listdir(IMAGES_DIR):
        if f.lower() == want:
            return f
    return None

def _label(key: str) -> str:
    return key[:1].upper() + key[1:].lower()

def _target_filename(key: str) -> str:
    return f"Tab_{_label(key)}.png"

def _confirm_filename(key: str) -> str:
    return f"Tab_{_label(key)}_Confirm.png"

# =========================
# ASSIST CLICK TAB
# =========================
def assist_click_tab(tab, bot_id=1, verbose=True, timeout=3.0):
    key = str(tab).strip().lower()
    cfg = TABS.get(key)

    if not cfg:
        if verbose:
            print(f"❌ Onbekende tab: {tab}")
            print(f"✅ Beschikbaar: {', '.join(TABS.keys())}")
        return False

    emo = cfg["emoji"]
    label = _label(key)
    target_area = cfg["target_area"]

    # =========================
    # 0) Confirm check (is al open?)
    # =========================
    confirm_img = _find_image(_confirm_filename(key))
    if not confirm_img:
        if verbose:
            print(f"❌ Image mist: {_confirm_filename(key)}")
        return False

    if detect_image(confirm_img, CONFIRM_AREA, bot_id, verbose=False):
        if verbose:
            print(f"{emo} {label} is al open ✅")
        return True

    # =========================
    # 1) Click target
    # =========================
    target_img = _find_image(_target_filename(key))
    if not target_img:
        if verbose:
            print(f"❌ Image mist: {_target_filename(key)}")
        return False

    if verbose:
        print(f"{emo} {label} openen…")

    clicked = click_image(target_img, target_area, bot_id, verbose=False)
    if not clicked:
        if verbose:
            print(f"{emo} {label} target niet gevonden ❌")
        return False

    # =========================
    # 2) Move outside (ALLEEN na succesvolle click)
    # =========================
    move_outside_area(MOVE_OUT_AREA, bot_id=bot_id)

    # =========================
    # 3) Wait confirm
    # =========================
    end = time.time() + float(timeout)
    checks = 0

    while time.time() < end:
        checks += 1
        if detect_image(confirm_img, CONFIRM_AREA, bot_id, verbose=False):
            if verbose:
                print(f"{emo} {label} bevestigd ✅ ({checks})")
            return True
        sleep_custom(0.12, 0.28)

    if verbose:
        print(f"{emo} {label} geen confirmation ⚠️")
    return False

# =========================
# TEST
# =========================
if __name__ == "__main__":
    BOT = 1
    print("🧪 Test tabs")
    for name in TABS.keys():
        print("\n---", name, "---")
        assist_click_tab(name, bot_id=BOT, verbose=True)
