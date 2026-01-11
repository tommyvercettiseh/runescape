from __future__ import annotations

import sys
from pathlib import Path
import cv2
import numpy as np
import pyautogui

# =========================
# BOOTSTRAP
# =========================
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# =========================
# CONFIG
# =========================
PARENT_AREA = "Inventory_Area_Pattern"
BOT_ID = 1

COLS = 4
ROWS = 7

ROI_SIZE_PCT = 40     # centre ROI grootte per cel
EDGE_THR = 0.018      # lager = sneller "EMPTY", hoger = sneller "FILLED"
CANNY1 = 60
CANNY2 = 140

# =========================
# AREAS
# =========================
def _load_areas():
    import json
    p = ROOT / "config" / "areas.json"
    return json.loads(p.read_text(encoding="utf-8-sig"))

def _get_area(areas, name):
    wanted = (name or "").strip().lower()
    for k, v in areas.items():
        if str(k).lower() == wanted:
            return v["coords"] if isinstance(v, dict) else v
    raise KeyError(f"Area niet gevonden: {name}")

def _get_offset(bot_id):
    try:
        from core.bot_offsets import get_offset
        return get_offset(int(bot_id))
    except Exception:
        return (0, 0)

# =========================
# GRID ROI
# =========================
def build_grid_rois(area_xyxy, cols, rows, roi_size_pct):
    x1, y1, x2, y2 = area_xyxy
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)

    cw = w / cols
    ch = h / rows
    s = max(0.05, min(1.0, roi_size_pct / 100.0))

    rois = []
    idx = 0
    for r in range(rows):
        for c in range(cols):
            cx1 = x1 + c * cw
            cy1 = y1 + r * ch
            cx2 = cx1 + cw
            cy2 = cy1 + ch

            ccx = (cx1 + cx2) / 2
            ccy = (cy1 + cy2) / 2
            rw = cw * s
            rh = ch * s

            rx1 = int(ccx - rw / 2)
            ry1 = int(ccy - rh / 2)
            rx2 = int(ccx + rw / 2)
            ry2 = int(ccy + rh / 2)

            rois.append((idx, rx1, ry1, rx2, ry2))
            idx += 1
    return rois

# =========================
# EDGE CHECK (EMPTY vs FILLED)
# =========================
def edge_ratio(roi_rgb, canny1, canny2):
    gray = cv2.cvtColor(roi_rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, canny1, canny2)
    return float(np.mean(edges > 0))  # 0..1

def slot_is_empty_by_edges(roi_rgb, thr, canny1, canny2):
    r = edge_ratio(roi_rgb, canny1, canny2)
    return (r < thr), r

# =========================
# MAIN
# =========================
def main():
    areas = _load_areas()
    base_xyxy = _get_area(areas, PARENT_AREA)

    ox, oy = _get_offset(BOT_ID)
    x1, y1, x2, y2 = base_xyxy
    abs_xyxy = (x1 + ox, y1 + oy, x2 + ox, y2 + oy)

    W = abs_xyxy[2] - abs_xyxy[0]
    H = abs_xyxy[3] - abs_xyxy[1]

    shot = pyautogui.screenshot(region=(abs_xyxy[0], abs_xyxy[1], W, H))
    img = np.array(shot)  # RGB

    rois = build_grid_rois((0, 0, W, H), COLS, ROWS, ROI_SIZE_PCT)

    empty_idxs = []
    filled_idxs = []
    results = []

    for idx, rx1, ry1, rx2, ry2 in rois:
        roi = img[ry1:ry2, rx1:rx2]
        if roi.size == 0:
            is_empty, val = True, 0.0
        else:
            is_empty, val = slot_is_empty_by_edges(roi, EDGE_THR, CANNY1, CANNY2)

        results.append((idx, val, is_empty))
        if is_empty:
            empty_idxs.append(idx)
        else:
            filled_idxs.append(idx)

    print("\n=== INVENTORY GRID CHECK (EDGES) ===")
    print(f"Parent: {PARENT_AREA} | Bot: {BOT_ID} | {COLS}x{ROWS} | ROI%={ROI_SIZE_PCT}")
    print(f"EDGE_THR={EDGE_THR} | CANNY=({CANNY1},{CANNY2})\n")

    print("idx\tedge_ratio\tstate")
    for idx, val, is_empty in results:
        print(f"{idx}\t{val:.4f}\t\t{'EMPTY' if is_empty else 'FILLED'}")

    print("\nEMPTY:", empty_idxs)
    print("FILLED:", filled_idxs)
    print("Count filled:", len(filled_idxs), "of", len(results))

if __name__ == "__main__":
    main()
