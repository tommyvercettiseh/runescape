from __future__ import annotations

import sys
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import ImageGrab

# ============================================================
# BOOTSTRAP
# WAT: Zorgt dat imports werken vanuit je project-root.
# WAAROM: Je wil dit script kunnen runnen vanaf elke map.
# ============================================================
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]  # Runescape/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================
# IMPORTS (project)
# ============================================================
from core.ai_cursor import move_and_click
from config.areas import load_coords

# ============================================================
# BOT OFFSETS
# ============================================================
BOT_OFFSETS = {
    1: (0, 0),
    2: (958, 0),
    3: (0, 498),
    4: (958, 498),
}

# ============================================================
# LOGGING
# ============================================================
def _log(icon: str, title: str, msg: str) -> None:
    print(f"{icon} {title}  {msg}")

def _title(msg: str) -> None:
    print(f"\n{'=' * 52}\n{msg}\n{'=' * 52}")

# ============================================================
# COLOURS (ingebouwd)
# HSV ranges: lower/upper
# ============================================================
COLOR_ALIASES = {
    "cyaan": "cyan",
    "paars": "purple",
    "roze": "pink",
    "groen": "green",
    "geel": "yellow",
    "oranje": "orange",
    "rood": "red",
    "blauw": "blue",
    "wit": "white",
    "zwart": "black",
}

COLOR_RANGES = {
    "cyan": ((80, 80, 80), (100, 255, 255)),
    "blue": ((100, 80, 60), (130, 255, 255)),
    "purple": ((130, 60, 60), (160, 255, 255)),
    "pink": ((160, 60, 60), (179, 255, 255)),
    "green": ((35, 70, 70), (85, 255, 255)),
    "yellow": ((20, 80, 80), (35, 255, 255)),
    "orange": ((10, 80, 80), (20, 255, 255)),
    "red": ((0, 80, 80), (10, 255, 255)),
    "white": ((0, 0, 200), (179, 45, 255)),
    "black": ((0, 0, 0), (179, 255, 45)),
}

# ============================================================
# HELPERS
# ============================================================
def _normalize_colour(kleur: str) -> str:
    k = (kleur or "").lower().strip()
    return COLOR_ALIASES.get(k, k)

def _area_bbox(area_name: str, bot_id: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = load_coords(area_name)
    ox, oy = BOT_OFFSETS.get(int(bot_id), (0, 0))
    return x1 + ox, y1 + oy, x2 + ox, y2 + oy

def _colour_mask_in_bbox(kleur: str, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    np_img = np.array(img)
    hsv = cv2.cvtColor(np_img, cv2.COLOR_RGB2HSV)

    lower, upper = map(np.array, COLOR_RANGES[kleur])
    return cv2.inRange(hsv, lower, upper)

def _mask_pct(mask: np.ndarray) -> float:
    return float((mask > 0).mean() * 100.0)

# ============================================================
# QUICK CHECK (optioneel)
# ============================================================
def has_colour_in_area(
    kleur: str,
    area_name: str,
    bot_id: int,
    threshold_pct: float = 10.0,
) -> bool:
    kleur = _normalize_colour(kleur)
    if kleur not in COLOR_RANGES:
        return False

    bbox = _area_bbox(area_name, bot_id)
    mask = _colour_mask_in_bbox(kleur, bbox)
    return _mask_pct(mask) >= float(threshold_pct)

# ============================================================
# CLICK COLOUR
# ============================================================
def click_colour(
    kleur: str,
    area_name: str,
    bot_id: int = 1,
    button: str = "left",
    threshold: float = 0.005,     # 0.5% default
    jitter_range: int = 6,
    min_size: int = 15,
    dilate_px: int = 2,           # helpt bij losse pixels/edges
    prefer_center: bool = True,   # nieuw: kies eerst dichtbij centrum
    center_bias: float = 0.0,     # 0.0 = puur centrum, 0.15 = centrum + liever groter
    verbose: bool = True,
) -> bool:
    kleur = _normalize_colour(kleur)

    if verbose:
        _title(f"🎯 Click Colour  {kleur.upper()} in {area_name}  (bot {bot_id})")

    if kleur not in COLOR_RANGES:
        if verbose:
            _log("❌", "Onbekende kleur", kleur)
        return False

    bbox = _area_bbox(area_name, bot_id)
    x1, y1, x2, y2 = bbox

    mask = _colour_mask_in_bbox(kleur, bbox)
    pct = _mask_pct(mask)

    if verbose:
        _log("🧪", "Detectie", f"mask dekking {pct:.2f}%  bbox=({x1},{y1},{x2},{y2})")

    # mask dikker maken (fix voor dunne outlines / anti-alias)
    if int(dilate_px) > 0:
        k = int(dilate_px) * 2 + 1
        kernel = np.ones((k, k), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        if verbose:
            _log("🧱", "Dilate", f"{dilate_px}px  kernel={k}x{k}")

    # zachte aanwezigheidscheck (geen harde return)
    min_pct = float(threshold) * 100.0
    if pct < min_pct and verbose:
        _log("🫥", "Te weinig kleur", f"{pct:.3f}% < {min_pct:.3f}%  (we proberen contours)")

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        if verbose:
            _log("🚫", "Geen target", f"geen contour gevonden voor {kleur}")
        return False

    contours = [c for c in contours if cv2.contourArea(c) >= int(min_size)]
    if not contours:
        if verbose:
            _log("📏", "Te klein", f"geen vlak ≥ {min_size}px voor {kleur}")
        return False

    # =========================
    # 1) Kies target: centrum → naar buiten
    # =========================
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2

    def _center_score(contour) -> float:
        M = cv2.moments(contour)
        if M["m00"] == 0:
            return 1e18
        cx0 = int(M["m10"] / M["m00"]) + x1
        cy0 = int(M["m01"] / M["m00"]) + y1

        dist2 = (cx0 - center_x) ** 2 + (cy0 - center_y) ** 2
        area0 = float(cv2.contourArea(contour))

        # lager is beter: afstand leidend, optioneel bonus voor grootte
        return dist2 - (float(center_bias) * area0)

    if prefer_center:
        gekozen = min(contours, key=_center_score)
        if verbose:
            _log("🧲", "Selectie", f"centrum eerst  (bias={center_bias})")
    else:
        gekozen = max(contours, key=cv2.contourArea)
        if verbose:
            _log("🏋️", "Selectie", "grootste vlak eerst")

    area_px = float(cv2.contourArea(gekozen))

    M = cv2.moments(gekozen)
    if M["m00"] == 0:
        if verbose:
            _log("⚠️", "Moments", "m00=0, kan centroid niet bepalen")
        return False

    cx = int(M["m10"] / M["m00"]) + x1
    cy = int(M["m01"] / M["m00"]) + y1

    # =========================
    # 2) Klik met kleine jitter
    # =========================
    tx = cx + random.randint(-int(jitter_range), int(jitter_range))
    ty = cy + random.randint(-int(jitter_range), int(jitter_range))

    if verbose:
        _log("🎯", "Target", f"centroid=({cx},{cy})  jitter=±{jitter_range}")
        _log("🖱️", "Klik", f"{kleur} | {area_px:.0f}px @ ({tx},{ty})  button={button}")

    move_and_click((tx, ty), button=button)

    if verbose:
        _log("✅", "Done", "click uitgevoerd")

    return True

# ============================================================
# RUN (test)
# ============================================================
if __name__ == "__main__":
    click_colour("paars", "Bot_Area", bot_id=1, prefer_center=True, center_bias=0.10, verbose=True)
