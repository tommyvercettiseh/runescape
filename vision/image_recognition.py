import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui

from core.paths import IMAGES_DIR
from core.bot_offsets import load_areas, apply_offset

METHODS = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

_TEMPLATE_CACHE = {}

def _load_template(image_path):
    p = Path(image_path)
    if not p.is_absolute():
        p = Path(IMAGES_DIR) / image_path
    p = p.resolve()

    key = str(p)
    if key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[key]

    bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden: {p}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _TEMPLATE_CACHE[key] = (rgb, gray)
    return rgb, gray

def _color_score(template_rgb, matched_rgb):
    if matched_rgb.shape[:2] != template_rgb.shape[:2]:
        matched_rgb = cv2.resize(matched_rgb, (template_rgb.shape[1], template_rgb.shape[0]))
    diff = cv2.absdiff(template_rgb, matched_rgb)
    mae = float(np.mean(diff))
    return round(max(0.0, 100.0 - mae), 2)

def _grab_area_rgb(box):
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    return np.array(pyautogui.screenshot(region=(x1, y1, w, h)))

def detect_image(image_path, area_name, method_name="TM_CCOEFF_NORMED", vorm_drempel=90, kleur_drempel=60, bot_id=1, areas=None):
    method = METHODS.get(method_name)
    if method is None:
        raise ValueError(f"Onbekende methode: {method_name}")

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    template_rgb, template_gray = _load_template(image_path)

    box = apply_offset(areas[area_name], bot_id)
    shot_rgb = _grab_area_rgb(box)
    shot_gray = cv2.cvtColor(shot_rgb, cv2.COLOR_RGB2GRAY)

    result = cv2.matchTemplate(shot_gray, template_gray, method)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    is_sqdiff = method_name in ("TM_SQDIFF", "TM_SQDIFF_NORMED")
    top_left = min_loc if is_sqdiff else max_loc

    vorm = (1.0 - float(min_val) if is_sqdiff else float(max_val)) * 100.0
    vorm = round(min(100.0, max(0.0, vorm)), 2)

    th, tw = template_rgb.shape[:2]
    if top_left[0] + tw > shot_rgb.shape[1] or top_left[1] + th > shot_rgb.shape[0]:
        return None

    matched = shot_rgb[top_left[1]:top_left[1] + th, top_left[0]:top_left[0] + tw]
    kleur = _color_score(template_rgb, matched)

    if vorm < float(vorm_drempel) or kleur < float(kleur_drempel):
        return None

    x1, y1, _, _ = box
    return {
        "x": int(x1 + top_left[0]),
        "y": int(y1 + top_left[1]),
        "width": int(tw),
        "height": int(th),
        "vorm": vorm,
        "kleur": kleur,
    }

def detect_image_timeout(image_path, area_name, method_name="TM_CCOEFF_NORMED", vorm_drempel=90, kleur_drempel=60, bot_id=1, timeout_sec=3.0, poll_sec=0.1, areas=None):
    deadline = time.time() + float(timeout_sec)
    while time.time() <= deadline:
        m = detect_image(image_path, area_name, method_name, vorm_drempel, kleur_drempel, bot_id, areas)
        if m:
            return m
        time.sleep(float(poll_sec))
    return None
