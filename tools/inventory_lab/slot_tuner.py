from __future__ import annotations

import cv2
import numpy as np
from PIL import ImageGrab

from core.ansi import ANSIx
from config.areas import load_coords
from core.bot_offsets import apply_offset

from tools.inventory_lab.slot_scan import _build_slots, GRID_COLS, GRID_ROWS


def _area_bbox(area_name, bot_id):
    x1, y1, x2, y2 = apply_offset(list(load_coords(area_name)), bot_id)
    return int(x1), int(y1), int(x2), int(y2)


def _grab_hsv(bbox):
    x1, y1, x2, y2 = bbox
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    rgb = np.array(img)
    if rgb.shape[-1] == 4:
        rgb = rgb[:, :, :3]
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)


def slot_tuner(bot_id=1, slot_index=0, patch=10):
    bbox = _area_bbox("Inventory_Area", bot_id)
    hsv = _grab_hsv(bbox)

    h, w = hsv.shape[:2]
    slots = _build_slots(w, h, pad=3)

    if slot_index < 0 or slot_index >= len(slots):
        print(ANSIx.fail(f"❌ slot_index out of range | 0..{len(slots)-1}"))
        return None

    x0, y0, x1, y1 = slots[slot_index]
    cx = int((x0 + x1) / 2)
    cy = int((y0 + y1) / 2)

    p = int(max(2, patch))
    roi = hsv[max(0, cy - p):cy + p, max(0, cx - p):cx + p]

    h_min, s_min, v_min = roi.reshape(-1, 3).min(axis=0).tolist()
    h_max, s_max, v_max = roi.reshape(-1, 3).max(axis=0).tolist()
    h_mean, s_mean, v_mean = roi.reshape(-1, 3).mean(axis=0).tolist()

    print(ANSIx.info(f"🧪 Slot tuner | bot {bot_id} | slot={slot_index} | grid={GRID_COLS}x{GRID_ROWS}"))
    print(ANSIx.ok(f"HSV mean: {(h_mean:.1f, s_mean:.1f, v_mean:.1f)}"))
    print(ANSIx.ok(f"HSV min : {(int(h_min), int(s_min), int(v_min))}"))
    print(ANSIx.ok(f"HSV max : {(int(h_max), int(s_max), int(v_max))}"))

    return {
        "slot": int(slot_index),
        "mean": (float(h_mean), float(s_mean), float(v_mean)),
        "min": (int(h_min), int(s_min), int(v_min)),
        "max": (int(h_max), int(s_max), int(v_max)),
    }


if __name__ == "__main__":
    print("🧪 Slot tuner\n")
    slot_tuner(bot_id=1, slot_index=0, patch=10)

# cd C:\Users\Hesse\Desktop\Runescape
# python -m tools.inventory_lab.slot_tuner