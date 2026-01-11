from __future__ import annotations

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
import time
import json

import cv2
import numpy as np
import pyautogui

from core.paths import IMAGES_DIR, CONFIG_DIR
from core.bot_offsets import load_areas, apply_offset

# ============================================================
# ANSI
# ============================================================
ANSI = {
    "groen": "\033[92m",
    "rood": "\033[91m",
    "cyaan": "\033[96m",
    "paars": "\033[95m",
    "reset": "\033[0m",
}

# ============================================================
# CONSTANTS
# ============================================================
METHODS = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

META_FILE = Path(CONFIG_DIR) / "templates_meta.json"
_TEMPLATE_CACHE = {}

# ============================================================
# HIT (zodat click_image hit.x werkt)
# ============================================================
class Hit:
    def __init__(self, x, y, width, height, vorm, kleur):
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
        self.vorm = float(vorm)
        self.kleur = float(kleur)

# ============================================================
# SETTINGS
# ============================================================
def _safe_read_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

def _load_template_settings(image_name):
    meta = _safe_read_json(META_FILE)
    d = meta.get(image_name, {})
    return {
        "method": d.get("method", "TM_CCOEFF"),
        "min_shape": float(d.get("min_shape", 85)),
        "min_color": float(d.get("min_color", 60)),
    }

# ============================================================
# TEMPLATE CACHE
# ============================================================
def _resolve_template_path(image_name):
    p = Path(image_name)
    return p if p.is_absolute() else Path(IMAGES_DIR) / image_name

def _read_template(image_name):
    path = _resolve_template_path(image_name)
    key = str(path.resolve())

    if key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[key]

    bgr = cv2.imread(str(path))
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden: {path}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    _TEMPLATE_CACHE[key] = (rgb, gray)
    return rgb, gray

# ============================================================
# SCORING
# ============================================================
def _scoremap_0_1(result, method_name):
    s = cv2.normalize(result, None, 0, 1, cv2.NORM_MINMAX)
    if method_name.startswith("TM_SQDIFF"):
        s = 1.0 - s
    return s

def _color_score(template_rgb, patch_rgb):
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(patch_rgb, template_rgb.shape[:2][::-1])
    diff = cv2.absdiff(template_rgb, patch_rgb)
    return float(np.clip(100 - np.mean(diff), 0, 100))

# ============================================================
# GRAB + MATCH
# ============================================================
def _grab_area_rgb(x1, y1, w, h):
    return np.array(pyautogui.screenshot(region=(x1, y1, w, h)))

def _best_match_in_shot(shot_rgb, tpl_rgb, tpl_gray, method_name):
    gray = cv2.cvtColor(shot_rgb, cv2.COLOR_RGB2GRAY)
    th, tw = tpl_gray.shape[:2]

    best_loc = None
    best_vorm = 0.0
    best_kleur = 0.0

    for mname, mval in METHODS.items():
        if method_name != "ALL" and mname != method_name:
            continue

        res = cv2.matchTemplate(gray, tpl_gray, mval)
        scoremap = _scoremap_0_1(res, mname)
        _, score, _, loc = cv2.minMaxLoc(scoremap)

        vorm = float(score * 100)
        rx, ry = int(loc[0]), int(loc[1])

        patch = shot_rgb[ry:ry + th, rx:rx + tw]
        if patch.shape[:2] != (th, tw):
            continue

        kleur = _color_score(tpl_rgb, patch)

        if vorm > best_vorm:
            best_vorm = vorm
            best_kleur = kleur
            best_loc = (rx, ry)

    return best_loc, round(best_vorm, 2), round(best_kleur, 2)

# ============================================================
# LOGGING (jouw stijl)
# ============================================================
def _pretty_label(image_name):
    return Path(image_name).stem.replace("_", " ").strip().title()

def _log_found(image_name, area_name):
    reset = ANSI["reset"]
    groen = ANSI["groen"]
    cyaan = ANSI["cyaan"]
    paars = ANSI["paars"]

    label = _pretty_label(image_name)

    print(
        f"{groen}🟢🖼️  Found{reset} | "
        f"{cyaan}{label}{reset} in "
        f"{paars}{area_name}{reset}"
    )

def _log_not_found(image_name, area_name):
    reset = ANSI["reset"]
    rood = ANSI["rood"]
    cyaan = ANSI["cyaan"]
    paars = ANSI["paars"]

    label = _pretty_label(image_name)

    print(
        f"{rood}🔴🖼️  Not found{reset} | "
        f"{cyaan}{label}{reset} in "
        f"{paars}{area_name}{reset}"
    )

# ============================================================
# API
# ============================================================
def detect_image(image_name, area_name, bot_id=1, areas=None, verbose=True):
    cfg = _load_template_settings(image_name)
    method = cfg["method"]
    min_shape = cfg["min_shape"]
    min_color = cfg["min_color"]

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    tpl_rgb, tpl_gray = _read_template(image_name)
    th, tw = tpl_gray.shape[:2]

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1

    shot = _grab_area_rgb(x1, y1, w, h)
    loc, vorm, kleur = _best_match_in_shot(shot, tpl_rgb, tpl_gray, method)

    ok = (loc is not None and vorm >= min_shape and kleur >= min_color)

    if verbose:
        if ok:
            _log_found(image_name, area_name)
        else:
            _log_not_found(image_name, area_name)

    if not ok:
        return None

    rx, ry = loc
    return Hit(
        x=x1 + rx,
        y=y1 + ry,
        width=tw,
        height=th,
        vorm=vorm,
        kleur=kleur,
    )

def detect_image_timeout(image_name, area_name, bot_id=1, timeout_sec=3, sleep_sec=0.1, areas=None, verbose=True):
    start = time.time()

    while time.time() - start < float(timeout_sec):
        hit = detect_image(image_name, area_name, bot_id=bot_id, areas=areas, verbose=False)
        if hit:
            if verbose:
                _log_found(image_name, area_name)
            return hit
        time.sleep(float(sleep_sec))

    if verbose:
        _log_not_found(image_name, area_name)
    return None

def detect_images(image_name, area_name, bot_id=1, areas=None, verbose=True, max_hits=60, nms_radius=0):
    """
    Vind ALLE hits (met dezelfde template settings als detect_image).
    Geeft list[Hit] terug met absolute coords.
    """
    cfg = _load_template_settings(image_name)
    method = cfg["method"]
    min_shape = cfg["min_shape"]
    min_color = cfg["min_color"]

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    tpl_rgb, tpl_gray = _read_template(image_name)
    th, tw = tpl_gray.shape[:2]

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1

    shot = _grab_area_rgb(x1, y1, w, h)
    gray = cv2.cvtColor(shot, cv2.COLOR_RGB2GRAY)

    method_names = list(METHODS.keys()) if method == "ALL" else [method]
    minimum_score_0_1 = float(min_shape) / 100.0

    hits = []

    for mname in method_names:
        mval = METHODS[mname]
        res = cv2.matchTemplate(gray, tpl_gray, mval)
        scoremap = _scoremap_0_1(res, mname)

        ys, xs = np.where(scoremap >= minimum_score_0_1)
        if len(xs) == 0:
            continue

        scores = scoremap[ys, xs]
        order = np.argsort(scores)[::-1]

        rad = int(nms_radius) if int(nms_radius) > 0 else max(6, int(min(tw, th) * 0.55))

        picked = []
        for idx in order:
            rx = int(xs[idx])
            ry = int(ys[idx])
            score_0_1 = float(scores[idx])
            vorm = float(score_0_1 * 100.0)

            too_close = False
            for px, py, _ in picked:
                dx = rx - px
                dy = ry - py
                if (dx * dx + dy * dy) <= (rad * rad):
                    too_close = True
                    break
            if too_close:
                continue

            patch = shot[ry:ry + th, rx:rx + tw]
            if patch.shape[:2] != (th, tw):
                continue

            kleur = _color_score(tpl_rgb, patch)
            if kleur < float(min_color):
                continue

            picked.append((rx, ry, vorm))

            hits.append(
                Hit(
                    x=x1 + rx,
                    y=y1 + ry,
                    width=tw,
                    height=th,
                    vorm=round(vorm, 2),
                    kleur=round(kleur, 2),
                )
            )

            if len(hits) >= int(max_hits):
                break

        if len(hits) >= int(max_hits):
            break

    if verbose:
        if hits:
            _log_found(image_name, area_name)
            print(f"✅ hits: {len(hits)}")
        else:
            _log_not_found(image_name, area_name)

    return hits




# ============================================================
# CLI TEST
# ============================================================
if __name__ == "__main__":
    print("⚠️ CLI test: zorg dat je doelvenster zichtbaar is. Start in 2s...")
    time.sleep(2)

    detect_image("xp.png", "Info_Area", bot_id=1, verbose=True)
