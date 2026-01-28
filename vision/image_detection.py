from __future__ import annotations

import sys
import time
import json
from pathlib import Path

import cv2
import numpy as np
import pyautogui

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.paths import IMAGES_DIR, CONFIG_DIR
from core.bot_offsets import load_areas, apply_offset
from helpers.log import log

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
# VERBOSE HELPERS
# ============================================================
def _is_verbose(v):
    if v is True:
        return True
    if v is False or v is None:
        return False
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("off", "false", "0", "no", "none", ""):
            return False
        return True
    return bool(v)

# ============================================================
# HIT
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
def _safe_read_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

def _load_template_settings(image_name: str):
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
# GRAB
# ============================================================
def _grab_area_rgb(x1, y1, w, h):
    return np.array(pyautogui.screenshot(region=(x1, y1, w, h)))

def _pretty_label(image_name):
    return Path(image_name).stem.replace("_", " ").strip().title()

# ============================================================
# LOGGING
# ============================================================
def _log_found(image_name, area_name, *, elapsed=None, trace=False, trace_depth=5, verbose=True, **_):
    if not _is_verbose(verbose):
        return

    reset = ANSI["reset"]
    groen = ANSI["groen"]
    cyaan = ANSI["cyaan"]
    paars = ANSI["paars"]

    label = _pretty_label(image_name)
    t = f" | {elapsed:.2f}s" if elapsed is not None else ""

    msg = (
        f"{groen}🟢🖼️  Found{reset} | "
        f"{cyaan}{label}{reset} in "
        f"{paars}{area_name}{reset}{t}"
    )
    log(True, msg, trace=trace, depth=trace_depth)

def _log_not_found(image_name, area_name, *, elapsed=None, trace=False, trace_depth=5, verbose=True, **_):
    if not _is_verbose(verbose):
        return

    reset = ANSI["reset"]
    rood = ANSI["rood"]
    cyaan = ANSI["cyaan"]
    paars = ANSI["paars"]

    label = _pretty_label(image_name)
    t = f" | {elapsed:.2f}s" if elapsed is not None else ""

    msg = (
        f"{rood}🔴🖼️  Not found{reset} | "
        f"{cyaan}{label}{reset} in "
        f"{paars}{area_name}{reset}{t}"
    )
    log(True, msg, trace=trace, depth=trace_depth)

def _log_hits_count(n, *, trace=False, trace_depth=5, verbose=True):
    if not _is_verbose(verbose):
        return
    log(True, f"✅ hits: {int(n)}", trace=trace, depth=trace_depth)

# ============================================================
# BEST MATCH (single best)
# ============================================================
def _best_match_in_shot(shot_rgb, tpl_rgb, tpl_gray, method_name):
    gray = cv2.cvtColor(shot_rgb, cv2.COLOR_RGB2GRAY)
    th, tw = tpl_gray.shape[:2]

    best_loc = None
    best_vorm = 0.0
    best_kleur = 0.0

    method_names = list(METHODS.keys()) if method_name == "ALL" else [method_name]

    for mname in method_names:
        mval = METHODS.get(mname)
        if mval is None:
            continue

        res = cv2.matchTemplate(gray, tpl_gray, mval)
        scoremap = _scoremap_0_1(res, mname)
        _, score, _, loc = cv2.minMaxLoc(scoremap)

        vorm = float(score * 100.0)
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
# SINGLE PASS CORE
# ============================================================
def _detect_image_once(
    image_name,
    area_name,
    *,
    bot_id=1,
    areas=None,
    verbose=False,
    subdir=None,
):
    cfg = _load_template_settings(image_name)
    method = cfg["method"]
    min_shape = float(cfg["min_shape"])
    min_color = float(cfg["min_color"])

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    tpl_rgb, tpl_gray = _read_template(image_name)
    th, tw = tpl_gray.shape[:2]

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1
    if w <= 1 or h <= 1:
        return None

    shot = _grab_area_rgb(x1, y1, w, h)
    loc, vorm, kleur = _best_match_in_shot(shot, tpl_rgb, tpl_gray, method)

    if not loc:
        return None
    if float(vorm) < float(min_shape):
        return None
    if float(kleur) < float(min_color):
        return None

    rx, ry = int(loc[0]), int(loc[1])

    return Hit(
        x=x1 + rx,
        y=y1 + ry,
        width=tw,
        height=th,
        vorm=round(float(vorm), 2),
        kleur=round(float(kleur), 2),
    )

# ============================================================
# API detect_image
# ============================================================
def detect_image(
    image_name,
    area_name,
    bot_id=1,
    areas=None,
    verbose=True,
    subdir=None,
    timeout=None,
    interval=1.0,
    trace=False,
    trace_depth=5,
):
    v = _is_verbose(verbose)
    start = time.time()

    hit = _detect_image_once(
        image_name,
        area_name,
        bot_id=bot_id,
        areas=areas,
        subdir=subdir,
    )
    if hit:
        _log_found(image_name, area_name, elapsed=time.time() - start, trace=trace, trace_depth=trace_depth, verbose=v)
        return hit

    if timeout is None or float(timeout) <= 0:
        _log_not_found(image_name, area_name, elapsed=time.time() - start, trace=trace, trace_depth=trace_depth, verbose=v)
        return None

    end = start + float(timeout)
    sleep_s = max(0.01, float(interval))

    while time.time() < end:
        time.sleep(sleep_s)

        hit = _detect_image_once(
            image_name,
            area_name,
            bot_id=bot_id,
            areas=areas,
            subdir=subdir,
        )
        if hit:
            _log_found(image_name, area_name, elapsed=time.time() - start, trace=trace, trace_depth=trace_depth, verbose=v)
            return hit

    _log_not_found(image_name, area_name, elapsed=time.time() - start, trace=trace, trace_depth=trace_depth, verbose=v)
    return None

# ============================================================
# API detect_images
# ============================================================
def detect_images(
    image_name,
    area_name,
    bot_id=1,
    areas=None,
    verbose=True,
    max_hits=60,
    nms_radius=0,
    trace=False,
    trace_depth=5,
):
    v = _is_verbose(verbose)

    cfg = _load_template_settings(image_name)
    method = cfg["method"]
    min_shape = float(cfg["min_shape"])
    min_color = float(cfg["min_color"])

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    tpl_rgb, tpl_gray = _read_template(image_name)
    th, tw = tpl_gray.shape[:2]

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1
    if w <= 1 or h <= 1:
        _log_not_found(image_name, area_name, trace=trace, trace_depth=trace_depth, verbose=v)
        return []

    shot = _grab_area_rgb(x1, y1, w, h)
    gray = cv2.cvtColor(shot, cv2.COLOR_RGB2GRAY)

    method_names = list(METHODS.keys()) if method == "ALL" else [method]
    minimum_score_0_1 = float(min_shape) / 100.0

    hits = []

    for mname in method_names:
        mval = METHODS.get(mname)
        if mval is None:
            continue

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

    if hits:
        _log_found(image_name, area_name, trace=trace, trace_depth=trace_depth, verbose=v)
        _log_hits_count(len(hits), trace=trace, trace_depth=trace_depth, verbose=v)
    else:
        _log_not_found(image_name, area_name, trace=trace, trace_depth=trace_depth, verbose=v)

    return hits

# ============================================================
# CLI TEST
# ============================================================
if __name__ == "__main__":
    print("⚠️ CLI test: zorg dat je doelvenster zichtbaar is. Start in 2s...")
    time.sleep(2)

    hit = detect_image("xp.png", "Info_Area", bot_id=1, verbose=True, timeout=5, interval=1.0)
    print(f"🏁 Result: {'OK ✅' if hit else 'FAIL ❌'}")
