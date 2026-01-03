# ============================================================
# BOOTSTRAP
# ============================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
import json
import cv2
import numpy as np
import pyautogui

from core.bot_offsets import apply_offset

# ============================================================


ANSI = {
    "groen": "\033[92m",
    "rood": "\033[91m",
    "geel": "\033[93m",
    "blauw": "\033[94m",
    "cyaan": "\033[96m",
    "paars": "\033[95m",
    "area": "\033[95m",   # paars voor area
    "reset": "\033[0m",
}



# CONFIG
# ============================================================
AREAS_FILE = ROOT / "config" / "areas.json"

COLOR_RANGES = {
    "groen": [((35, 50, 50), (85, 255, 255))],
    "rood":  [((0, 80, 80), (10, 255, 255)), ((170, 80, 80), (179, 255, 255))],
    "geel":  [((20, 80, 80), (35, 255, 255))],
    "blauw": [((95, 50, 50), (135, 255, 255))],
    "cyaan": [((82, 50, 50), (98, 255, 255))],
    "paars": [((135, 50, 50), (170, 255, 255))],
}

COLOR_ALIASES = {
    "green": "groen",
    "g": "groen",
    "red": "rood",
    "r": "rood",
    "yellow": "geel",
    "y": "geel",
    "blue": "blauw",
    "b": "blauw",
    "cyan": "cyaan",
    "c": "cyaan",
    "purple": "paars",
    "p": "paars",
}

FULLSCREEN = {"fullscreen", "screen", "full", "full_screen", "full screen"}


# ============================================================
# AREAS
# ============================================================
def load_areas():
    if not AREAS_FILE.exists():
        return {}

    try:
        data = json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))
    except:
        return {}

    out = {}
    for name, v in data.items():
        if isinstance(v, dict) and "coords" in v:
            out[name] = v["coords"]
        elif isinstance(v, list):
            out[name] = v
    return out


def grab_area_rgb(area, bot_id=1, areas=None):
    if areas is None:
        areas = load_areas()

    if area.lower() in FULLSCREEN:
        return np.array(pyautogui.screenshot())

    key = None
    for k in areas:
        if k.lower() == area.lower():
            key = k
            break

    if key is None:
        raise Exception(f"Area niet gevonden: {area}")

    x1, y1, x2, y2 = apply_offset(areas[key], bot_id)
    w = x2 - x1
    h = y2 - y1

    return np.array(pyautogui.screenshot(region=(x1, y1, w, h)))


# ============================================================
# CORE
# ============================================================
def detect_colour(colour, area, percentage, bot_id=1, verbose=False, blur=3, areas=None):
    colour = COLOR_ALIASES.get(colour.lower(), colour.lower())

    rgb = grab_area_rgb(area, bot_id=bot_id, areas=areas)

    if blur >= 3:
        if blur % 2 == 0:
            blur += 1
        rgb = cv2.GaussianBlur(rgb, (blur, blur), 0)

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    ranges = COLOR_RANGES.get(colour)
    if not ranges:
        if verbose:
            print(f"❌ onbekende kleur: {colour}")
        return False

    mask = None
    for lo, hi in ranges:
        m = cv2.inRange(hsv, np.array(lo), np.array(hi))
        mask = m if mask is None else cv2.bitwise_or(mask, m)

    percent = (mask > 0).mean() * 100
    ok = percent >= percentage

    if verbose:
        kleur_label = colour.capitalize()
        pct = f"{percent:.2f}".replace(".", ",")
        min_pct = f"{percentage}".replace(".", ",")
        status = "found" if ok else "not found"
        icon = "🟢" if ok else "🔴"

        kleur_ansi = ANSI.get(colour, "")
        area_ansi = ANSI["area"]
        reset = ANSI["reset"]

        print(
            f"{icon} "
            f"{kleur_ansi}{kleur_label}{reset} {status} in "
            f"{area_ansi}{area}{reset} | "
            f"{pct}% | Min {min_pct}% | Bot = {bot_id}"
        )


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    print(detect_colour("green", "Skilling_Area", 3, bot_id=1, verbose=True))
