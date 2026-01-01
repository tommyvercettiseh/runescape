from __future__ import annotations

# === START BOOTSTRAP ===
# • WAT: zorgt dat imports vanuit project-root werken bij direct runnen.
# • WAAROM: voorkomt "No module named core" als je dit script direct runt.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# === END BOOTSTRAP ===


# === START IMPORTS ===
# • WAT: libs voor screenshot + HSV kleurdetectie.
# • WAAROM: pyautogui pakt pixels, OpenCV telt pixels in HSV masks.
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
import pyautogui

from core.bot_offsets import load_areas, apply_offset
# === END IMPORTS ===


# === START COLOR CONFIG ===
# • WAT: HSV ranges per kleur (OpenCV: H 0..179, S/V 0..255)
# • WAAROM: HSV is robuuster voor kleurdetectie dan RGB.
HSVRange = Tuple[Tuple[int, int, int], Tuple[int, int, int]]

COLOR_RANGES: Dict[str, List[HSVRange]] = {
    "groen": [((35, 50, 50), (85, 255, 255))],
    "rood":  [((0, 80, 80), (10, 255, 255)), ((170, 80, 80), (179, 255, 255))],
    "geel":  [((20, 80, 80), (35, 255, 255))],
    "blauw": [((95, 50, 50), (135, 255, 255))],
    "cyaan": [((82, 50, 50), (98, 255, 255))],   # strakker (minder overlap met blauw)
    "paars": [((135, 50, 50), (170, 255, 255))],
}

COLOR_EMOJI = {
    "groen": "🟢",
    "rood": "🔴",
    "geel": "🟡",
    "blauw": "🔵",
    "cyaan": "🔷",
    "paars": "🟣",
}

STATUS_EMOJI = {
    "groen": "🟢",
    "rood": "🔴",
    "niet_zichtbaar": "⚫",
}
# === END COLOR CONFIG ===


# === START HELPERS ===
def pretty_name(name: str) -> str:
    return name.replace("_", " ").capitalize()

def _pct(v: float) -> int:
    return int(round(v))

def _grab_area_rgb(area_name: str, *, bot_id: int = 1, areas=None) -> np.ndarray:
    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1
    return np.array(pyautogui.screenshot(region=(x1, y1, w, h)))  # RGB

def _mask_for_color(hsv: np.ndarray, color: str) -> np.ndarray:
    ranges = COLOR_RANGES.get(color)
    if not ranges:
        # runtime safe: onbekende kleur -> lege mask (0%)
        return np.zeros(hsv.shape[:2], dtype=np.uint8)

    mask_total = None
    for lo, hi in ranges:
        m = cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
        mask_total = m if mask_total is None else cv2.bitwise_or(mask_total, m)
    return mask_total
# === END HELPERS ===


# === START COLOR TELLER ===
def color_teller(
    area_name: str,
    *,
    bot_id: int = 1,
    colors: Optional[List[str]] = None,
    blur: int = 3,
    areas=None,
) -> Dict[str, float]:
    colors = [c.lower() for c in (colors or list(COLOR_RANGES.keys()))]

    rgb = _grab_area_rgb(area_name, bot_id=bot_id, areas=areas)

    if blur and blur >= 3:
        k = blur if blur % 2 == 1 else blur + 1
        rgb = cv2.GaussianBlur(rgb, (k, k), 0)

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    out: Dict[str, float] = {}
    for c in colors:
        mask = _mask_for_color(hsv, c)
        out[c] = float((mask > 0).mean() * 100.0)

    return out
# === END COLOR TELLER ===


# === START SIMPLE DETECT ===
def detect_colour(
    colour: str,
    area_name: str,
    *,
    bot_id: int = 1,
    min_pct: float = 5.0,
    blur: int = 3,
    areas=None,
) -> tuple[bool, float]:
    colour = colour.lower()
    t = color_teller(area_name, bot_id=bot_id, colors=[colour], blur=blur, areas=areas)
    pct = float(t.get(colour, 0.0))
    return pct >= min_pct, pct

def detect_colour_from_teller(
    teller: Dict[str, float],
    colour: str,
    *,
    min_pct: float = 5.0,
) -> tuple[bool, float]:
    colour = colour.lower()
    pct = float(teller.get(colour, 0.0))
    return pct >= min_pct, pct
# === END SIMPLE DETECT ===


# === START RED/GREEN CHECKER ===
def red_green_status(teller: Dict[str, float], *, min_pct: float = 8.0) -> str:
    groen = float(teller.get("groen", 0.0))
    rood = float(teller.get("rood", 0.0))

    if groen >= min_pct and groen > rood:
        return "groen"
    if rood >= min_pct and rood > groen:
        return "rood"
    return "niet_zichtbaar"
# === END RED/GREEN CHECKER ===


# === START PRETTY PRINTS ===
def print_summary(
    area_name: str,
    bot_id: int,
    teller_all: Dict[str, float],
    *,
    min_status_pct: float = 8.0,
) -> None:
    items = sorted(teller_all.items(), key=lambda x: x[1], reverse=True)
    winner, win_pct = (items[0][0], items[0][1]) if items else ("onbekend", 0.0)

    status = red_green_status(teller_all, min_pct=min_status_pct)
    g = _pct(teller_all.get("groen", 0.0))
    r = _pct(teller_all.get("rood", 0.0))

    print(f"📍 Area: {area_name}  🤖 Bot: {bot_id}")
    print(
        f"🏆 Dominant: {COLOR_EMOJI.get(winner,'⬜')} {pretty_name(winner)} {_pct(win_pct)}%  |  "
        f"{STATUS_EMOJI[status]} Status: {pretty_name(status)} (🟢 {g}% | 🔴 {r}%)"
    )

def print_colors_line(teller: Dict[str, float], *, order: List[str], min_pct: float = 1.0) -> None:
    parts = []
    for c in order:
        c = c.lower()
        v = float(teller.get(c, 0.0))
        if v < min_pct:
            continue
        parts.append(f"{COLOR_EMOJI.get(c,'⬜')} {pretty_name(c)} {_pct(v)}%")
    print(" | ".join(parts) if parts else "⚫ Geen kleuren boven drempel")
# === END PRETTY PRINTS ===


# === START CLI TEST ===
if __name__ == "__main__":
    AREA = "Bot_Area"
    BOT = 1
    ORDER = ["blauw", "cyaan", "paars", "groen", "geel", "rood"]

    # 1 screenshot, alles uit dezelfde teller halen
    t_all = color_teller(AREA, bot_id=BOT, colors=ORDER, blur=3)

    print_summary(AREA, BOT, t_all, min_status_pct=8.0)
    print_colors_line(t_all, order=ORDER, min_pct=1.0)

    # voorbeeld: losse check zonder extra screenshot
    ok, pct = detect_colour_from_teller(t_all, "groen", min_pct=8.0)
    if ok:
        print(f"✅ Groen gezien ({_pct(pct)}%)")
    else:
        print(f"❌ Geen groen ({_pct(pct)}%)")
# === END CLI TEST ===
