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
# AREAS 📍
# =========================
TOP = "Buttons_Top"
BOTTOM = "Buttons_Bottom"
CONFIRM_AREA = "Tab_Confirmation_Area"
MOVE_OUT_AREA = "Info_Area"

# =========================
# TABS PRESETS 🧭
# =========================
TABS = {
    "fight":     {"emoji": "⚔️", "target_area": TOP},
    "skilling":  {"emoji": "📚", "target_area": TOP},
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
# IMAGE HELPERS 🖼️
# =========================
def _find_image(name: str) -> str | None:
    want = name.lower()
    for f in os.listdir(IMAGES_DIR):
        if f.lower() == want:
            return f
    return None

def _label(key: str) -> str:
    s = str(key).strip()
    return s[:1].upper() + s[1:].lower()

def _target_filename(key: str) -> str:
    return f"Tab_{_label(key)}.png"

def _confirm_filename(key: str) -> str:
    return f"Tab_{_label(key)}_Confirm.png"

# =========================
# ASSIST CLICK TAB 🧭
# =========================
def assist_click_tab(tab, bot_id=1, verbose=True, timeout=3.0):
    key = str(tab).strip().lower()
    cfg = TABS.get(key)

    if not cfg:
        if verbose:
            print(f"❌  🧭  Onbekende tab        | {tab}")
            print(f"✅  🧭  Beschikbaar          | {', '.join(sorted(TABS.keys()))}")
        return False

    emo = cfg["emoji"]
    label = _label(key)
    target_area = cfg["target_area"]

    # =========================
    # 0) Confirm check ✅ (al open?)
    # =========================
    confirm_name = _confirm_filename(key)
    confirm_img = _find_image(confirm_name)
    if not confirm_img:
        verbose and print(f"❌  🖼️  Mist image           | {confirm_name}")
        return False

    if detect_image(confirm_img, CONFIRM_AREA, bot_id, verbose=False):
        verbose and print(f"✅  {emo}  Tab al open        | {label}")
        return True

    # =========================
    # 1) Click target 🎯
    # =========================
    target_name = _target_filename(key)
    target_img = _find_image(target_name)
    if not target_img:
        verbose and print(f"❌  🖼️  Mist image           | {target_name}")
        return False

    verbose and print(f"⏳  {emo}  Tab openen          | {label}")

    clicked = click_image(target_img, target_area, bot_id, verbose=False)
    if not clicked:
        verbose and print(f"❌  {emo}  Target niet gevonden | {label}")
        return False

    verbose and print(f"✅  {emo}  Click gedaan         | {label}")

    # =========================
    # 2) Move outside 🧭 (alleen na click)
    # =========================
    move_outside_area(MOVE_OUT_AREA, bot_id=bot_id)

    # =========================
    # 3) Wait confirm ⏳
    # =========================
    end = time.time() + float(timeout)
    checks = 0

    while time.time() < end:
        checks += 1
        if detect_image(confirm_img, CONFIRM_AREA, bot_id, verbose=False):
            verbose and print(f"✅  {emo}  Bevestigd           | {label}   ({checks})")
            return True
        sleep_custom(0.12, 0.28)

    verbose and print(f"⚠️  {emo}  Geen confirmation    | {label}")
    return False

# =========================
# TEST 🧪
# =========================
if __name__ == "__main__":
    BOT = 1
    print("🧪  Test tabs\n")

    assist_click_tab("Inventory", bot_id=1, verbose=True, timeout=3.0)

    for name in TABS.keys():
        label = _label(name)
        print(f"🧭  Test tab   | {label}")
        assist_click_tab(name, bot_id=BOT, verbose=True)
        print()
