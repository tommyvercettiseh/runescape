from __future__ import annotations

import sys
import json
from pathlib import Path

import numpy as np
import cv2

try:
    import mss
except ImportError:
    raise SystemExit("pip install mss")

# =========================
# BOOTSTRAP
# =========================
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bot_offsets import get_offset  # noqa: E402

AREAS_FILE = ROOT / "config" / "areas.json"

# =========================
# CONFIG
# =========================
BOT_ID = 1
SLOT_PREFIX = "Inventory_Slot_"
TOTAL_SLOTS = 28

COLS = 4
ROWS = 7

BG_RANGES = [((8, 38, 44), (21, 87, 100))]
EMPTY_BG_PCT_THRESHOLD = 0.90

SAVE_GRID_IMAGE = True
OUT_DIR = ROOT / "debug" / "inventory_grid"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "inventory_grid.png"


# =========================
# HELPERS
# =========================
def load_areas():
    if not AREAS_FILE.exists():
        raise SystemExit(f"areas.json niet gevonden: {AREAS_FILE}")
    return json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))


def area_xyxy(data, area_name: str, bot_id: int):
    x1, y1, x2, y2 = data[area_name]["coords"]
    ox, oy = get_offset(bot_id)
    return (x1 + ox, y1 + oy, x2 + ox, y2 + oy)


def grab_bgr(x1, y1, x2, y2):
    w = max(1, int(x2 - x1))
    h = max(1, int(y2 - y1))
    with mss.mss() as sct:
        mon = {"left": int(x1), "top": int(y1), "width": w, "height": h}
        img = np.array(sct.grab(mon))  # BGRA
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def bg_pct(hsv_img, ranges):
    mask_total = np.zeros(hsv_img.shape[:2], dtype=np.uint8)
    for lo, hi in ranges:
        lo = np.array(lo, dtype=np.uint8)
        hi = np.array(hi, dtype=np.uint8)
        mask = cv2.inRange(hsv_img, lo, hi)
        mask_total = cv2.bitwise_or(mask_total, mask)
    return float(np.count_nonzero(mask_total)) / float(mask_total.size)


def slot_name(i: int):
    return f"{SLOT_PREFIX}{i}"


def make_grid_image(slot_states):
    """
    slot_states: list of dicts with keys:
      idx, empty(bool), pct(float 0..1)
    """
    cell = 80
    pad = 10
    w = COLS * cell + pad * 2
    h = ROWS * cell + pad * 2
    img = np.zeros((h, w, 3), dtype=np.uint8)

    for s in slot_states:
        i = s["idx"]
        r = (i - 1) // COLS
        c = (i - 1) % COLS

        x1 = pad + c * cell
        y1 = pad + r * cell
        x2 = x1 + cell - 2
        y2 = y1 + cell - 2

        # Groen als empty, rood als bezet (BGR)
        color = (0, 180, 0) if s["empty"] else (0, 0, 200)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness=-1)

        label = f"{i}"
        pct_txt = f"{s['pct']*100:.0f}%"
        cv2.putText(img, label, (x1 + 8, y1 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(img, pct_txt, (x1 + 8, y1 + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(
        img,
        f"bot={BOT_ID}  thr={EMPTY_BG_PCT_THRESHOLD*100:.0f}%",
        (pad, h - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )
    return img


def main():
    data = load_areas()

    slot_states = []
    for i in range(1, TOTAL_SLOTS + 1):
        name = slot_name(i)
        if name not in data:
            print(f"⚠️ ontbreekt: {name}")
            continue

        x1, y1, x2, y2 = area_xyxy(data, name, BOT_ID)
        bgr = grab_bgr(x1, y1, x2, y2)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

        pct = bg_pct(hsv, BG_RANGES)
        empty = pct >= EMPTY_BG_PCT_THRESHOLD

        slot_states.append({"idx": i, "empty": empty, "pct": pct})

    # Print grid
    print(f"🧪 Inventory grid test | bot={BOT_ID}")
    print(f"BG_RANGES={BG_RANGES}")
    print(f"Empty threshold={EMPTY_BG_PCT_THRESHOLD*100:.1f}%\n")

    for r in range(ROWS):
        row_cells = []
        row_pcts = []
        for c in range(COLS):
            i = r * COLS + c + 1
            st = next((x for x in slot_states if x["idx"] == i), None)
            if not st:
                row_cells.append("??")
                row_pcts.append("   ?")
                continue

            row_cells.append("🟩" if st["empty"] else "🟥")
            row_pcts.append(f"{st['pct']*100:5.1f}")

        print(" ".join(row_cells) + "    " + " ".join(row_pcts))

    occupied = [s["idx"] for s in slot_states if not s["empty"]]
    print("\n📌 Bezet slots:", occupied if occupied else "(none)")

    # Save image
    if SAVE_GRID_IMAGE:
        img = make_grid_image(slot_states)
        cv2.imwrite(str(OUT_FILE), img)
        print(f"🖼️ Saved: {OUT_FILE}")


if __name__ == "__main__":
    main()
