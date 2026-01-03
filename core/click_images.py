from __future__ import annotations
import sys, time, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
import pyautogui

from pynput.mouse import Controller
from ai_cursor import move_and_click  # :contentReference[oaicite:2]{index=2}

from click_image import (
    DEFAULT_MOTION,
    DEFAULT_CLICK,
    humanize_motion,
    humanize_click,
    maybe_micro_pause,
)  # :contentReference[oaicite:3]{index=3}


def _normalize_png(name):
    name = (name or "").strip()
    if not name:
        return name
    return name if name.lower().endswith(".png") else name + ".png"


def _get_template_dir():
    try:
        import vision.image_detection as v
        d = getattr(v, "TEMPLATE_DIR", None)
        if d:
            return Path(d)
    except Exception:
        pass
    return ROOT / "assets" / "templates"


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


def _get_offset(bot_id):
    try:
        from core.bot_offsets import BOT_OFFSETS
        return BOT_OFFSETS.get(int(bot_id), (0, 0))
    except Exception:
        return (0, 0)


def _nms(boxes, scores, iou_thr=0.25):
    # boxes: [[x1,y1,x2,y2], ...] in IMAGE coords (region local)
    if len(boxes) == 0:
        return []

    boxes = np.array(boxes, dtype=np.float32)
    scores = np.array(scores, dtype=np.float32)

    x1 = boxes[:, 0]; y1 = boxes[:, 1]; x2 = boxes[:, 2]; y2 = boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)

        inds = np.where(iou <= iou_thr)[0]
        order = order[inds + 1]

    return keep


def click_all_hits(
    image_name,
    area_name,
    bot_id=1,
    threshold=0.90,
    padding=2,
    min_pause=0.08,
    max_pause=0.25,
    iou_thr=0.25,
    max_clicks=999,
    shuffle_hits=True,
    verbose=True,
):
    img = _normalize_png(image_name)

    areas = _load_areas()
    if area_name not in areas:
        raise KeyError(f"area bestaat niet: {area_name}")

    x1, y1, x2, y2 = areas[area_name]
    ox, oy = _get_offset(bot_id)
    x1 += ox; y1 += oy; x2 += ox; y2 += oy

    w = max(1, x2 - x1)
    h = max(1, y2 - y1)

    template_dir = _get_template_dir()
    template_path = template_dir / img
    if not template_path.exists():
        raise FileNotFoundError(f"template niet gevonden: {template_path}")

    if verbose:
        print(f"🔎 scan area={area_name} bot={bot_id} thr={threshold} template={img}")

    shot = pyautogui.screenshot(region=(x1, y1, w, h))
    hay_rgb = np.array(shot)
    hay_bgr = cv2.cvtColor(hay_rgb, cv2.COLOR_RGB2BGR)

    tpl_bgr = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if tpl_bgr is None:
        raise RuntimeError(f"kan template niet laden: {template_path}")

    th, tw = tpl_bgr.shape[:2]
    res = cv2.matchTemplate(hay_bgr, tpl_bgr, cv2.TM_CCOEFF_NORMED)

    ys, xs = np.where(res >= float(threshold))
    if len(xs) == 0:
        if verbose:
            print("⚠️ geen hits")
        return []

    boxes = []
    scores = []
    for (x, y) in zip(xs, ys):
        boxes.append([x, y, x + tw, y + th])
        scores.append(float(res[y, x]))

    keep = _nms(boxes, scores, iou_thr=iou_thr)
    hits = []
    for i in keep:
        bx1, by1, bx2, by2 = boxes[i]
        sc = scores[i]
        hits.append((int(bx1), int(by1), int(bx2), int(by2), sc))

    if shuffle_hits:
        random.shuffle(hits)
    else:
        hits.sort(key=lambda t: t[4], reverse=True)

    if verbose:
        print(f"✅ hits gevonden: {len(hits)}")

    ctrl = Controller()
    clicked_points = []

    for idx, (bx1, by1, bx2, by2, sc) in enumerate(hits[: int(max_clicks)], start=1):
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
            print(f"🖱️ {idx}/{min(len(hits), max_clicks)} score={sc:.3f} @ ({screen_x},{screen_y})")

        maybe_micro_pause(0.18)
        m = humanize_motion(DEFAULT_MOTION)
        c = humanize_click(DEFAULT_CLICK)
        move_and_click((screen_x, screen_y), motion=m, click_cfg=c, controller=ctrl)

        clicked_points.append((screen_x, screen_y))
        time.sleep(random.uniform(min_pause, max_pause))

    return clicked_points


if __name__ == "__main__":
    # voorbeeld: 28 smileys in 1 area
    click_all_hits("smiley", "Some_Area", 1, threshold=0.88, max_clicks=200)
