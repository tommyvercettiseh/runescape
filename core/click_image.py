from __future__ import annotations

import sys
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # Runescape/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
import pyautogui

# ✅ BELANGRIJK: ai_cursor zit in core/
from core.ai_cursor import move_and_click


_TEMPLATE_INDEX_CACHE = {}


def _normalize_png(name):
    name = (name or "").strip()
    if not name:
        return name
    return name if name.lower().endswith(".png") else name + ".png"


def _norm_key(s):
    return (s or "").strip().lower().replace(" ", "_")


def _get_template_dir():
    # 1) als je vision.image_detection TEMPLATE_DIR hebt
    try:
        import vision.image_detection as v
        d = getattr(v, "TEMPLATE_DIR", None)
        if d and Path(d).exists():
            return Path(d)
    except Exception:
        pass

    # 2) als je core.paths IMAGES_DIR hebt
    try:
        from core.paths import IMAGES_DIR
        if IMAGES_DIR and Path(IMAGES_DIR).exists():
            return Path(IMAGES_DIR)
    except Exception:
        pass

    # 3) fallback assets/images
    p = ROOT / "assets" / "images"
    if p.exists():
        return p

    # 4) laatste fallback
    return ROOT / "assets" / "templates"


def _build_template_index(template_dir):
    idx = {}
    if not template_dir.exists():
        return idx

    for p in template_dir.iterdir():
        if p.is_file() and p.suffix.lower() == ".png":
            idx[_norm_key(p.stem)] = p
    return idx


def _resolve_template_path(template_dir, image_name):
    wanted = _norm_key(Path(_normalize_png(image_name)).stem)

    idx = _TEMPLATE_INDEX_CACHE.get(template_dir)
    if idx is None:
        idx = _build_template_index(template_dir)
        _TEMPLATE_INDEX_CACHE[template_dir] = idx

    hit = idx.get(wanted)
    if hit:
        return hit

    # refresh cache 1x (handig tijdens testen)
    idx = _build_template_index(template_dir)
    _TEMPLATE_INDEX_CACHE[template_dir] = idx
    hit = idx.get(wanted)
    if hit:
        return hit

    raise FileNotFoundError(
        f"template niet gevonden: '{image_name}' (genorm='{wanted}') in {template_dir}"
    )


def _load_areas():
    try:
        from core.bot_offsets import load_areas
        return load_areas()
    except Exception:
        pass

    p = ROOT / "config" / "areas.json"
    if not p.exists():
        raise FileNotFoundError(f"areas.json niet gevonden: {p}")

    import json
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_area(areas, area_name):
    wanted = (area_name or "").strip().lower()
    for k, v in areas.items():
        if str(k).lower() == wanted:
            return v
    raise KeyError(f"area bestaat niet: {area_name}")


def _get_offset(bot_id):
    try:
        from core.bot_offsets import BOT_OFFSETS
        return BOT_OFFSETS.get(int(bot_id), (0, 0))
    except Exception:
        return (0, 0)


def click_image(image_name, area_name, bot_id=1, threshold=0.90, padding=2, verbose=True):
    areas = _load_areas()
    x1, y1, x2, y2 = _get_area(areas, area_name)

    ox, oy = _get_offset(bot_id)
    x1 += ox; y1 += oy; x2 += ox; y2 += oy

    w = max(1, x2 - x1)
    h = max(1, y2 - y1)

    template_dir = _get_template_dir()
    template_path = _resolve_template_path(template_dir, image_name)

    if verbose:
        print(f"🔍 click_image area={area_name} bot={bot_id} thr={threshold} template={template_path.name}")

    shot = pyautogui.screenshot(region=(x1, y1, w, h))
    hay_rgb = np.array(shot)
    hay_bgr = cv2.cvtColor(hay_rgb, cv2.COLOR_RGB2BGR)

    tpl_bgr = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if tpl_bgr is None:
        if verbose:
            print("❌ template niet geladen")
        return False

    th, tw = tpl_bgr.shape[:2]
    res = cv2.matchTemplate(hay_bgr, tpl_bgr, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    if max_val < threshold:
        if verbose:
            print(f"⚠️ geen hit ({max_val:.3f} < {threshold})")
        return False

    bx1, by1 = max_loc
    bx2, by2 = bx1 + tw, by1 + th

    pad = max(0, int(padding))
    ix1 = bx1 + pad; iy1 = by1 + pad
    ix2 = bx2 - pad; iy2 = by2 - pad
    if ix2 <= ix1 or iy2 <= iy1:
        ix1, iy1, ix2, iy2 = bx1, by1, bx2, by2

    px = random.randint(ix1, max(ix1, ix2 - 1))
    py = random.randint(iy1, max(iy1, iy2 - 1))

    screen_x = x1 + px
    screen_y = y1 + py

    if verbose:
        print(f"🖱️ click @ ({screen_x},{screen_y}) score={max_val:.3f}")

    move_and_click((screen_x, screen_y))
    return True


if __name__ == "__main__":
    click_image("Close_Screen_X.png", "Bot_Area", bot_id=1, threshold=0.88)
