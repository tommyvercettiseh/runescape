from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pyautogui

from core.paths import IMAGES_DIR
from core.bot_offsets import load_areas, apply_offset


METHODS: Dict[str, int] = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

_TEMPLATE_CACHE: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}


@dataclass(frozen=True)
class Match:
    x: int
    y: int
    width: int
    height: int
    vorm: float


def _read_template_gray(image_path: str) -> np.ndarray:
    full = Path(image_path)
    if not full.is_absolute():
        full = Path(IMAGES_DIR) / image_path

    key = str(full.resolve())
    if key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[key][1]

    bgr = cv2.imread(str(full), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden: {full}")

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _TEMPLATE_CACHE[key] = (bgr, gray)
    return gray


def detect_one(
    image_path: str,
    area_name: str,
    bot_id: int = 1,
    method_name: str = "TM_CCOEFF_NORMED",
    vorm_drempel: float = 90.0,
    areas: Optional[Dict[str, List[int]]] = None,
) -> Optional[Match]:
    method = METHODS.get(method_name)
    if method is None:
        raise ValueError(f"Onbekende methode: {method_name}")

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    template_gray = _read_template_gray(image_path)

    x1, y1, x2, y2 = apply_offset(areas[area_name], bot_id)
    w, h = x2 - x1, y2 - y1

    shot_rgb = np.array(pyautogui.screenshot(region=(x1, y1, w, h)))
    shot_gray = cv2.cvtColor(shot_rgb, cv2.COLOR_RGB2GRAY)

    result = cv2.matchTemplate(shot_gray, template_gray, method)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    is_sqdiff = method_name in ("TM_SQDIFF", "TM_SQDIFF_NORMED")
    top_left = min_loc if is_sqdiff else max_loc

    vorm = (1.0 - float(min_val) if is_sqdiff else float(max_val)) * 100.0
    vorm = round(min(100.0, max(0.0, vorm)), 2)

    if vorm < float(vorm_drempel):
        return None

    th, tw = template_gray.shape[:2]
    return Match(
        x=x1 + int(top_left[0]),
        y=y1 + int(top_left[1]),
        width=int(tw),
        height=int(th),
        vorm=vorm,
    )
