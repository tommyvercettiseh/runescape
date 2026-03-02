from __future__ import annotations

import json
import time
from pathlib import Path
from PIL import ImageGrab
import cv2
import numpy as np

from config.areas import load_coords
from core.bot_offsets import apply_offset


CONFIG_FILE = Path(__file__).resolve().parent / "slot_scan_config.json"

DEFAULT_CFG = {
    "bg_hsv_ranges": [((0, 0, 0), (179, 80, 120))],
    "empty_bg_pct": 0.72,
    "pad": 8,
    "grid_cols": 4,
    "grid_rows": 7,
    "area": "Inventory_Area",
}


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
    except Exception:
        pass
    return cfg


def save_cfg(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _area_bbox(area_name, bot_id):
    x1, y1, x2, y2 = apply_offset(list(load_coords(area_name)), bot_id)
    return int(x1), int(y1), int(x2), int(y2)


def _grab_hsv(bbox):
    x1, y1, x2, y2 = bbox
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    rgb = np.array(img)
    if rgb.shape[-1] == 4:
        rgb = rgb[:, :, :3]
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV), img


def _bg_mask(hsv, bg_hsv_ranges):
    mask = None
    for lo, hi in bg_hsv_ranges:
        lo = np.array(lo, dtype=np.uint8)
        hi = np.array(hi, dtype=np.uint8)
        m = cv2.inRange(hsv, lo, hi)
        mask = m if mask is None else cv2.bitwise_or(mask, m)
    return mask


def _build_slots(w, h, grid_cols, grid_rows, pad):
    slot_w = w / grid_cols
    slot_h = h / grid_rows
    slots = []
    for r in range(grid_rows):
        for c in range(grid_cols):
            x0 = int(c * slot_w) + pad
            y0 = int(r * slot_h) + pad
            x1 = int((c + 1) * slot_w) - pad
            y1 = int((r + 1) * slot_h) - pad
            slots.append((x0, y0, x1, y1))
    return slots


def scan_slots(bot_id=1, area=None, empty_bg_pct=None, pad=None, debug=False):
    cfg = load_cfg()
    area = area or cfg["area"]
    empty_bg_pct = float(cfg["empty_bg_pct"] if empty_bg_pct is None else empty_bg_pct)
    pad = int(cfg["pad"] if pad is None else pad)

    grid_cols = int(cfg["grid_cols"])
    grid_rows = int(cfg["grid_rows"])

    bg_ranges = cfg["bg_hsv_ranges"]
    bg_ranges = [tuple(map(tuple, r)) for r in bg_ranges]

    bbox = _area_bbox(area, bot_id)
    hsv, pil_img = _grab_hsv(bbox)
    mask = _bg_mask(hsv, bg_ranges)

    h, w = mask.shape[:2]
    slots = _build_slots(w, h, grid_cols, grid_rows, pad)

    empty_slots = []
    filled_slots = []
    bg_pcts = []

    for i, (x0, y0, x1, y1) in enumerate(slots):
        roi = mask[y0:y1, x0:x1]
        if roi.size == 0:
            filled_slots.append(i)
            bg_pcts.append(0.0)
            continue

        bg_pct = float((roi > 0).mean())
        bg_pcts.append(bg_pct)

        if bg_pct >= empty_bg_pct:
            empty_slots.append(i)
        else:
            filled_slots.append(i)

    result = {
        "bot_id": int(bot_id),
        "area": str(area),
        "bbox": bbox,
        "empty_bg_pct": float(empty_bg_pct),
        "pad": int(pad),
        "slots_total": len(slots),
        "empty_slots": empty_slots,
        "filled_slots": filled_slots,
        "empty_count": len(empty_slots),
        "filled_count": len(filled_slots),
        "bg_pcts": bg_pcts,
        "ts": time.time(),
    }

    if debug:
        result["slots_xyxy_local"] = slots
        result["pil_img"] = pil_img

    return result


def inventory_fill_count(bot_id=1):
    r = scan_slots(bot_id=bot_id, debug=False)
    return int(r["filled_count"])


def is_inventory_full(bot_id=1, threshold=28):
    return inventory_fill_count(bot_id=bot_id) >= int(threshold)