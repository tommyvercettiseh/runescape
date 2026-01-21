from __future__ import annotations

import sys
import json
from pathlib import Path

import numpy as np
import cv2

try:
    import mss
except ImportError:
    raise SystemExit("Installeer eerst: pip install mss")

# =========================
# BOOTSTRAP
# =========================
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bot_offsets import get_offset  # jouw offsets

AREAS_FILE = ROOT / "config" / "areas.json"


# =========================
# CONFIG
# =========================
BOT_ID = 1

SLOT_PREFIX = "Inventory_Slot_"
SLOTS = list(range(1, 29))

# Zet hier je verwachte BACKGROUND HSV range(s)
# Tip: begin breed, daarna strak maken
BG_RANGES = [
    # (lowerHSV, upperHSV)
    ((0, 0, 0), (179, 60, 120)),
]

# Als BG% >= threshold dan is het "empty"
EMPTY_BG_PCT_THRESHOLD = 0.92

# Print ook mean HSV per slot
PRINT_MEAN_HSV = True

# Debug images opslaan?
SAVE_DEBUG = False
DEBUG_DIR = ROOT / "debug" / "inventory_hsv"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# HELPERS
# =========================
def load_areas():
    if not AREAS_FILE.exists():
        raise SystemExit(f"areas.json niet gevonden: {AREAS_FILE}")
    return json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))


def get_slot_xyxy(data, slot_name: str, bot_id: int):
    if slot_name not in data:
        return None
    x1, y1, x2, y2 = data[slot_name]["coords"]
    ox, oy = get_offset(bot_id)
    return (x1 + ox, y1 + oy, x2 + ox, y2 + oy)


def grab_bgr(x1, y1, x2, y2):
    w = max(1, int(x2 - x1))
    h = max(1, int(y2 - y1))
    with mss.mss() as sct:
        mon = {"left": int(x1), "top": int(y1), "width": w, "height": h}
        img = np.array(sct.grab(mon))  # BGRA
    bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return bgr


def hsv_stats(hsv_img):
    # Mean HSV in slot (handig om je background te leren)
    mean = hsv_img.reshape(-1, 3).mean(axis=0)
    return tuple(float(x) for x in mean)


def bg_mask_pct(hsv_img, ranges):
    mask_total = np.zeros(hsv_img.shape[:2], dtype=np.uint8)
    for lo, hi in ranges:
        lo = np.array(lo, dtype=np.uint8)
        hi = np.array(hi, dtype=np.uint8)
        mask = cv2.inRange(hsv_img, lo, hi)
        mask_total = cv2.bitwise_or(mask_total, mask)

    bg_pixels = int(np.count_nonzero(mask_total))
    total = int(mask_total.size)
    pct = (bg_pixels / total) if total else 0.0
    return pct, mask_total


def main():
    data = load_areas()
    print(f"🔎 Inventory HSV probe | bot={BOT_ID}")
    print(f"BG ranges: {BG_RANGES}")
    print(f"Empty threshold: {EMPTY_BG_PCT_THRESHOLD*100:.1f}% BG\n")

    results = []

    for i in SLOTS:
        slot_name = f"{SLOT_PREFIX}{i}"
        xyxy = get_slot_xyxy(data, slot_name, BOT_ID)
        if not xyxy:
            print(f"⚠️ ontbreekt in areas.json: {slot_name}")
            continue

        x1, y1, x2, y2 = xyxy
        bgr = grab_bgr(x1, y1, x2, y2)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

        mean_h, mean_s, mean_v = hsv_stats(hsv) if PRINT_MEAN_HSV else (0, 0, 0)
        bg_pct, mask = bg_mask_pct(hsv, BG_RANGES)

        empty = bg_pct >= EMPTY_BG_PCT_THRESHOLD
        status = "🟩 EMPTY" if empty else "🟥 BEZET"

        if PRINT_MEAN_HSV:
            print(f"{slot_name:>16}  {status}  BG={bg_pct*100:6.2f}%  meanHSV=({mean_h:6.1f},{mean_s:6.1f},{mean_v:6.1f})")
        else:
            print(f"{slot_name:>16}  {status}  BG={bg_pct*100:6.2f}%")

        if SAVE_DEBUG:
            cv2.imwrite(str(DEBUG_DIR / f"{slot_name}_bgr.png"), bgr)
            cv2.imwrite(str(DEBUG_DIR / f"{slot_name}_mask.png"), mask)

        results.append((slot_name, bg_pct, empty, (mean_h, mean_s, mean_v)))

    # Samenvatting
    occupied = [r for r in results if not r[2]]
    print("\n📊 Samenvatting")
    print(f"Slots getest : {len(results)}")
    print(f"Bezet        : {len(occupied)}")

    if occupied:
        print("Bezet slots  :", ", ".join([x[0].split('_')[-1] for x in occupied]))


if __name__ == "__main__":
    main()
