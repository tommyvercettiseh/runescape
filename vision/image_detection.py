from __future__ import annotations

# === START BOOTSTRAP ===
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# === END BOOTSTRAP ===


# === START IMPORTS ===
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pyautogui

from core.paths import IMAGES_DIR, CONFIG_DIR
from core.bot_offsets import load_areas, apply_offset
# === END IMPORTS ===


# === START CONSTANTS ===
METHODS: Dict[str, int] = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

META_FILE = Path(CONFIG_DIR) / "templates_meta.json"
_TEMPLATE_CACHE: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

VERBOSE_OFF = "off"
VERBOSE_SHORT = "short"
VERBOSE_DEBUG = "debug"
# === END CONSTANTS ===


# === START MODELS ===
@dataclass(frozen=True)
class Match:
    x: int
    y: int
    width: int
    height: int
    vorm: float
    kleur: float
    method: str
# === END MODELS ===


# === START SETTINGS ===
def _safe_read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        import json
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _load_template_settings(image_name: str) -> dict:
    meta = _safe_read_json(META_FILE)
    d = meta.get(image_name, {})
    return {
        "method": d.get("method", "TM_CCOEFF"),
        "min_shape": float(d.get("min_shape", 85)),
        "min_color": float(d.get("min_color", 60)),
    }
# === END SETTINGS ===


# === START TEMPLATE CACHE ===
def _resolve_template_path(image_name: str) -> Path:
    p = Path(image_name)
    return p if p.is_absolute() else Path(IMAGES_DIR) / image_name


def _read_template(image_name: str):
    path = _resolve_template_path(image_name)
    key = str(path.resolve())

    if key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[key]

    bgr = cv2.imread(str(path))
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden: {path}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    _TEMPLATE_CACHE[key] = (bgr, rgb, gray)
    return bgr, rgb, gray
# === END TEMPLATE CACHE ===


# === START SCORING ===
def _scoremap_0_1(result: np.ndarray, method: str) -> np.ndarray:
    s = cv2.normalize(result, None, 0, 1, cv2.NORM_MINMAX)
    if method.startswith("TM_SQDIFF"):
        s = 1.0 - s
    return s


def _color_score(template_rgb: np.ndarray, patch_rgb: np.ndarray) -> float:
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(patch_rgb, template_rgb.shape[:2][::-1])
    diff = cv2.absdiff(template_rgb, patch_rgb)
    return float(np.clip(100 - np.mean(diff), 0, 100))
# === END SCORING ===


# === START LOGGING ===
def _log(image: str, ok: bool, area: str, bot: int, hit: Optional[Match], verbose: str):
    if not ok:
        print(f"🔴 {image} not found in {area} for bot {bot}")
        return

    print(
        f"🟢 {image} found in {area} for bot {bot} | "
        f"Vorm={int(hit.vorm)}% | Kleur={int(hit.kleur)}% | method={hit.method}"
    )

    if verbose == VERBOSE_DEBUG:
        print(f"   abs_xy=({hit.x},{hit.y}) size=({hit.width}x{hit.height})")
# === END LOGGING ===


# === START API ===
def detect_image(
    image_name: str,
    area_name: str,
    bot_id: int = 1,
    areas: Optional[Dict[str, List[int]]] = None,
    verbose: str = "short",
) -> Optional[Match]:

    cfg = _load_template_settings(image_name)
    method = cfg["method"]
    min_shape = cfg["min_shape"]
    min_color = cfg["min_color"]

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    _, tpl_rgb, tpl_gray = _read_template(image_name)
    th, tw = tpl_gray.shape[:2]

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1

    shot = np.array(pyautogui.screenshot(region=(x1, y1, w, h)))
    gray = cv2.cvtColor(shot, cv2.COLOR_RGB2GRAY)

    best: Optional[Match] = None

    for mname, mval in METHODS.items():
        if method != "ALL" and mname != method:
            continue

        res = cv2.matchTemplate(gray, tpl_gray, mval)
        scoremap = _scoremap_0_1(res, mname)
        _, score, _, loc = cv2.minMaxLoc(scoremap)

        vorm = score * 100
        if vorm < min_shape:
            continue

        rx, ry = map(int, loc)
        patch = shot[ry:ry+th, rx:rx+tw]
        if patch.shape[:2] != (th, tw):
            continue

        kleur = _color_score(tpl_rgb, patch)
        if kleur < min_color:
            continue

        hit = Match(x1+rx, y1+ry, tw, th, vorm, kleur, mname)
        if not best or hit.vorm > best.vorm:
            best = hit

    _log(image_name, bool(best), area_name, bot_id, best, verbose)
    return best
# === END API ===


# === START CLI TEST ===
if __name__ == "__main__":
    detect_image("jagex.png", "Bot_Area", bot_id=1, verbose="short")
# === END CLI TEST ===
