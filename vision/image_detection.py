"""vision.image_detection

Eén entrypoint voor je bots:

    hit = detect_one("jagex.png", area_name="FullScreen", bot_id=1)

Standaard leest hij per template de preset uit:
    config/templates_meta.json

Die file wordt gevuld door tools/image_debugger.py.

Preset velden (per template):
    method: "TM_CCOEFF_NORMED" | "ALL" | ...
    min_shape: 0..100
    min_color: 0..100

"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pyautogui

from core.paths import IMAGES_DIR, CONFIG_DIR
from core.bot_offsets import load_areas, apply_offset


METHODS: Dict[str, int] = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

META_FILE = Path(CONFIG_DIR) / "templates_meta.json"

# cache: key -> (template_rgb, template_gray)
_TEMPLATE_CACHE: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}


@dataclass(frozen=True)
class Match:
    x: int
    y: int
    width: int
    height: int
    vorm: float
    kleur: float
    method: str


def _safe_read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        import json

        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def _resolve_template_path(image_name_or_path: str) -> Path:
    p = Path(image_name_or_path)
    return p if p.is_absolute() else (Path(IMAGES_DIR) / image_name_or_path)


def _read_template_rgb_gray(image_name_or_path: str) -> Tuple[np.ndarray, np.ndarray]:
    full = _resolve_template_path(image_name_or_path).resolve()
    key = str(full)
    if key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[key]

    bgr = cv2.imread(str(full), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden: {full}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _TEMPLATE_CACHE[key] = (rgb, gray)
    return rgb, gray


def _scoremap_0_1(match_result: np.ndarray, method_name: str) -> np.ndarray:
    s = cv2.normalize(match_result, None, 0.0, 1.0, cv2.NORM_MINMAX)
    if method_name in ("TM_SQDIFF", "TM_SQDIFF_NORMED"):
        s = 1.0 - s
    return s


def _color_score_0_100(template_rgb: np.ndarray, patch_rgb: np.ndarray) -> float:
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(patch_rgb, (template_rgb.shape[1], template_rgb.shape[0]))
    diff = cv2.absdiff(template_rgb, patch_rgb)
    mae = float(np.mean(diff))
    return float(np.clip(100.0 - mae, 0.0, 100.0))


def _load_preset_for_template(image_name: str) -> dict:
    meta = _safe_read_json(META_FILE)
    d = meta.get(image_name, {}) if isinstance(meta, dict) else {}
    return {
        "method": str(d.get("method", "TM_CCOEFF_NORMED")),
        "min_shape": float(d.get("min_shape", 85.0)),
        "min_color": float(d.get("min_color", 60.0)),
    }


def detect_one(
    image_name: str,
    area_name: str,
    bot_id: int = 1,
    method_name: Optional[str] = None,
    min_shape: Optional[float] = None,
    min_color: Optional[float] = None,
    areas: Optional[Dict[str, List[int]]] = None,
) -> Optional[Match]:
    """Vind de beste match (1 hit).

    Defaults:
      method/min_shape/min_color worden uit templates_meta.json gehaald.

    method_name kan ook "ALL" zijn.
    """

    preset = _load_preset_for_template(image_name)
    method_name = (method_name or preset["method"]).strip()
    min_shape = float(min_shape if min_shape is not None else preset["min_shape"])
    min_color = float(min_color if min_color is not None else preset["min_color"])

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    template_rgb, template_gray = _read_template_rgb_gray(image_name)

    x1, y1, x2, y2 = apply_offset(areas[area_name], bot_id)
    w, h = x2 - x1, y2 - y1
    shot_rgb = np.array(pyautogui.screenshot(region=(x1, y1, w, h)))
    shot_gray = cv2.cvtColor(shot_rgb, cv2.COLOR_RGB2GRAY)

    th, tw = template_gray.shape[:2]
    if shot_gray.shape[0] < th or shot_gray.shape[1] < tw:
        return None

    def run_method(mname: str) -> Optional[Match]:
        if mname not in METHODS:
            return None

        raw = cv2.matchTemplate(shot_gray, template_gray, METHODS[mname])
        scores = _scoremap_0_1(raw, mname)
        _, best, _, best_loc = cv2.minMaxLoc(scores)
        x, y = int(best_loc[0]), int(best_loc[1])

        vorm = float(best) * 100.0
        patch = shot_rgb[y : y + th, x : x + tw]
        if patch.shape[:2] != (th, tw):
            return None
        kleur = _color_score_0_100(template_rgb, patch)

        if vorm < min_shape or kleur < min_color:
            return None

        return Match(
            x=x1 + x,
            y=y1 + y,
            width=int(tw),
            height=int(th),
            vorm=round(vorm, 2),
            kleur=round(kleur, 2),
            method=mname,
        )

    if method_name.upper() == "ALL":
        best_hit: Optional[Match] = None
        for m in METHODS.keys():
            hit = run_method(m)
            if not hit:
                continue
            if (best_hit is None) or (hit.vorm > best_hit.vorm):
                best_hit = hit
        return best_hit

    return run_method(method_name)
