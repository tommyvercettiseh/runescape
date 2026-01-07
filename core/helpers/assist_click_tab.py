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

# ============================================================
# AREAS
# ============================================================
TOP = "Buttons_Top"
BOTTOM = "Buttons_Bottom"
CONFIRM_AREA = "Tab_Confirmation_Area"

# ============================================================
# TABS PRESETS (alleen dit onderhouden)
# ============================================================
TABS = {
    # Top row
    "fight":     {"emoji": "⚔️", "target_area": TOP},
    "skills":    {"emoji": "📚", "target_area": TOP},
    "inventory": {"emoji": "🎒", "target_area": TOP},
    "equipment": {"emoji": "🧰", "target_area": TOP},
    "prayer":    {"emoji": "🙏", "target_area": TOP},
    "spellbook": {"emoji": "📜", "target_area": TOP},

    # Bottom row
    "friends":   {"emoji": "👥", "target_area": BOTTOM},
    "logout":    {"emoji": "🚪", "target_area": BOTTOM},
    "settings":  {"emoji": "⚙️", "target_area": BOTTOM},
    "music":     {"emoji": "🎵", "target_area": BOTTOM},
}

# ============================================================
# IMAGE RESOLVER (case-insensitive)
# jouw naming: Tab_Equipment.png / Tab_Equipment_Confirm.png
# ============================================================

def _find_image_case_insensitive(filename):
    want = filename.lower()
    for f in os.listdir(IMAGES_DIR):
        if f.lower() == want:
            return f
    return None

def _pretty_name(tab_key):
    # "spellbook" -> "Spellbook"
    return tab_key[:1].upper() + tab_key[1:].lower()

def _tab_images(tab_key):
    pretty = _pretty_name(tab_key)
    target = _find_image_case_insensitive(f"Tab_{pretty}.png")
    confirm = _find_image_case_insensitive(f"Tab_{pretty}_Confirm.png")
    return target, confirm

# ============================================================
# ASSIST
# ============================================================
def assist_click_tab(tab, bot_id=1, verbose=True, timeout=3.0):
    key = str(tab).strip().lower()
    cfg = TABS.get(key)

    if not cfg:
        if verbose:
            print(f"❌ Onbekende tab: {tab}")
            print(f"✅ Beschikbaar: {', '.join(TABS.keys())}")
        return False

    target_image, confirm_image = _tab_images(key)
    if not target_image or not confirm_image:
        if verbose:
            pretty = _pretty_name(key)
            miss = []
            if not target_image:
                miss.append(f"Tab_{pretty}.png")
            if not confirm_image:
                miss.append(f"Tab_{pretty}_Confirm.png")
            print(f"❌ Images missen voor '{key}': {', '.join(miss)}")
        return False

    emo = cfg.get("emoji", "🟦")
    label = _pretty_name(key)
    target_area = cfg["target_area"]

    # 0) al open
    if detect_image(confirm_image, CONFIRM_AREA, bot_id, verbose=False):
        if verbose:
            print(f"{emo} {label} is al open ✅")
        return True

    # 1) click target
    if verbose:
        print(f"{emo} {label} openen…")

    if not click_image(target_image, target_area, bot_id, verbose=False):
        if verbose:
            print(f"{emo} {label} target niet gevonden ❌")
        return False

    # 2) wait confirm
    end = time.time() + timeout
    checks = 0

    while time.time() < end:
        checks += 1
        if detect_image(confirm_image, CONFIRM_AREA, bot_id, verbose=False):
            if verbose:
                print(f"{emo} {label} bevestigd ✅ ({checks})")
            return True
        sleep_custom(0.12, 0.28)

    if verbose:
        print(f"{emo} {label} geen confirmation ⚠️")
    return False

# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    BOT = 1
    print("🧪 Test tabs")
    for name in TABS.keys():
        print("\n---", name, "---")
        assist_click_tab(name, bot_id=BOT, verbose=True)
