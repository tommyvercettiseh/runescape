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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bot_offsets import get_offset

AREAS_FILE = ROOT / "config" / "areas.json"

BOT_ID = 1
SLOT_PREFIX = "Inventory_Slot_"
SLOTS = list(range(1, 29))

# Calibratie: pak alleen de “meest background-achtige” pixels per slot
# Hoe hoger, hoe strakker je de echte background pakt
LOW_S_PERCENTILE = 40   # neem pixels met S <= dit percentile
LOW_V_PERCENTILE = 60   # en V <= dit percentile

# Range bouwen uit verzamelde background pixels
H_PAD = 6
S_PAD = 20
V_PAD = 25

# Threshold om empty te noemen (na calibratie)
EMPTY_BG_PCT_THRESHOLD = 0.90


def load_areas():
    return json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))


def get_slot_xyxy(data, slot_name: str, bot_id: int):
    x1, y1, x2, y2 = data[slot_name]["coords"]
    ox, oy = get_offset(bot_id)
    return (x1 + ox, y1 + oy, x2 + ox, y2 + oy)


def grab_bgr(x1, y1, x2, y2):
    w = max(1, int(x2 - x1))
    h = max(1, int(y2 - y1))
    with mss.mss() as sct:
        mon = {"left": int(x1), "top": int(y1), "width": w, "height": h}
        img = np.array(sct.grab(mon))
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def learn_bg_pixels(hsv):
    # flatten
    pixels = hsv.reshape(-1, 3).astype(np.float32)
    S = pixels[:, 1]
    V = pixels[:, 2]

    s_thr = np.percentile(S, LOW_S_PERCENTILE)
    v_thr = np.percentile(V, LOW_V_PERCENTILE)

    bg = pixels[(S <= s_thr) & (V <= v_thr)]
    if bg.size == 0:
        # fallback: pak 10% donkerste pixels op V
        v_thr2 = np.percentile(V, 10)
        bg = pixels[V <= v_thr2]
    return bg


def build_range(bg_pixels):
    # percentiles zodat outliers niet slopen
    H = bg_pixels[:, 0]
    S = bg_pixels[:, 1]
    V = bg_pixels[:, 2]

    h_lo = np.percentile(H, 5) - H_PAD
    h_hi = np.percentile(H, 95) + H_PAD
    s_lo = np.percentile(S, 5) - S_PAD
    s_hi = np.percentile(S, 95) + S_PAD
    v_lo = np.percentile(V, 5) - V_PAD
    v_hi = np.percentile(V, 95) + V_PAD

    # clamp HSV
    h_lo = max(0, int(h_lo)); h_hi = min(179, int(h_hi))
    s_lo = max(0, int(s_lo)); s_hi = min(255, int(s_hi))
    v_lo = max(0, int(v_lo)); v_hi = min(255, int(v_hi))

    return (h_lo, s_lo, v_lo), (h_hi, s_hi, v_hi)


def bg_pct(hsv, lo, hi):
    lo = np.array(lo, dtype=np.uint8)
    hi = np.array(hi, dtype=np.uint8)
    mask = cv2.inRange(hsv, lo, hi)
    return float(np.count_nonzero(mask)) / float(mask.size)


def main():
    data = load_areas()
    print(f"🎛️ Inventory HSV calibrate | bot={BOT_ID}")

    all_bg = []

    # 1) Verzamel background pixels uit alle slots
    for i in SLOTS:
        slot = f"{SLOT_PREFIX}{i}"
        x1, y1, x2, y2 = get_slot_xyxy(data, slot, BOT_ID)
        bgr = grab_bgr(x1, y1, x2, y2)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

        bg = learn_bg_pixels(hsv)
        if bg is not None and bg.size:
            all_bg.append(bg)

    if not all_bg:
        raise SystemExit("Geen background pixels kunnen leren 🤨")

    bg_pixels = np.vstack(all_bg)
    lo, hi = build_range(bg_pixels)

    print(f"\n✅ Learned BG range:")
    print(f"LOW = {lo}")
    print(f"HIGH= {hi}")
    print(f"Threshold empty: {EMPTY_BG_PCT_THRESHOLD*100:.1f}%\n")

    # 2) Test per slot met de learned range
    empty_count = 0
    for i in SLOTS:
        slot = f"{SLOT_PREFIX}{i}"
        x1, y1, x2, y2 = get_slot_xyxy(data, slot, BOT_ID)
        bgr = grab_bgr(x1, y1, x2, y2)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

        pct = bg_pct(hsv, lo, hi)
        empty = pct >= EMPTY_BG_PCT_THRESHOLD
        empty_count += 1 if empty else 0

        status = "🟩 EMPTY" if empty else "🟥 BEZET"
        mean = hsv.reshape(-1, 3).mean(axis=0)
        print(f"{slot:>16}  {status}  BG={pct*100:6.2f}%  meanHSV=({mean[0]:6.1f},{mean[1]:6.1f},{mean[2]:6.1f})")

    print("\n📊 Samenvatting")
    print(f"Slots leeg : {empty_count}/28")

    print("\n📌 Copy dit naar je inventory dropper config:")
    print(f"BG_RANGES = [({lo}, {hi})]")


if __name__ == "__main__":
    main()
