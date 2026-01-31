from __future__ import annotations

import sys
import json
from pathlib import Path

import cv2
import numpy as np

try:
    import mss
except ImportError:
    raise SystemExit("pip install mss")

# ============================================================
# BOOTSTRAP (AUTO: zoekt Runescape root)
# ============================================================
HERE = Path(__file__).resolve()
ROOT = None
for p in [HERE] + list(HERE.parents):
    if (p / "core").exists() and (p / "config").exists():
        ROOT = p
        break

if ROOT is None:
    raise SystemExit("❌ Project root niet gevonden (map met 'core' en 'config').")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS (project)
# ============================================================
from core.bot_offsets import get_offset
from vision.image_detection import detect_images
from helpers.ops import wait_until
from helpers.log import log

# ============================================================
# CONFIG
# ============================================================
BG_RANGES = [((8, 38, 44), (21, 87, 100))]
EMPTY_BG_PCT_THRESHOLD = 0.90  # >= 90% = leeg (🟩)

EXCLUDE_SLOTS = set()          # bv {1, 28}
EXCLUDE_IMAGES = []            # bv ["Item_Tinderbox.png", "Item_Axe.png"]

SLOT_PREFIX = "Inventory_Slot_"
TOTAL_SLOTS = 28
INVENTORY_AREA = "Inventory_Area"

# ============================================================
# HELPERS
# ============================================================
def _load_areas():
    p = ROOT / "config" / "areas.json"
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _normalize_png(name):
    name = (name or "").strip()
    if not name:
        return name
    return name if name.lower().endswith(".png") else name + ".png"


def _xyxy_for_area(data, area_name: str, bot_id: int):
    x1, y1, x2, y2 = data[area_name]["coords"]
    ox, oy = get_offset(bot_id)
    return (int(x1 + ox), int(y1 + oy), int(x2 + ox), int(y2 + oy))


def _slot_names(prefix=SLOT_PREFIX, total=TOTAL_SLOTS):
    return [f"{prefix}{i}" for i in range(1, total + 1)]


def _grab_bgr(x1, y1, x2, y2):
    w = max(1, int(x2 - x1))
    h = max(1, int(y2 - y1))
    with mss.mss() as sct:
        mon = {"left": int(x1), "top": int(y1), "width": w, "height": h}
        img = np.array(sct.grab(mon))
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def _bg_pct(hsv_img, ranges):
    mask_total = np.zeros(hsv_img.shape[:2], dtype=np.uint8)
    for lo, hi in ranges:
        lo = np.array(lo, dtype=np.uint8)
        hi = np.array(hi, dtype=np.uint8)
        mask = cv2.inRange(hsv_img, lo, hi)
        mask_total = cv2.bitwise_or(mask_total, mask)
    return float(np.count_nonzero(mask_total)) / float(mask_total.size)


def _wait_until_hits(img, area_name, bot_id, timeout, interval, max_hits):
    out = wait_until(
        lambda: detect_images(img, area_name, bot_id=bot_id, verbose="off", max_hits=max_hits),
        timeout=timeout,
        interval=interval,
    )
    return out or []


def _hit_center(hit):
    return (int(hit.x + hit.width / 2), int(hit.y + hit.height / 2))


def _point_in_xyxy(px, py, xyxy):
    x1, y1, x2, y2 = xyxy
    return x1 <= px <= x2 and y1 <= py <= y2


def _hit_to_slot_index(hit, slots_xyxy):
    px, py = _hit_center(hit)
    for idx, xyxy in enumerate(slots_xyxy, start=1):
        if _point_in_xyxy(px, py, xyxy):
            return idx
    return None


def _excluded_slots_from_images(
    *,
    bot_id,
    inventory_area,
    slot_prefix,
    total_slots,
    exclude_images,
    timeout,
    interval,
    verbose,
    trace,
    trace_depth,
):
    if not exclude_images:
        return set()

    data = _load_areas()
    slots = [f"{slot_prefix}{i}" for i in range(1, total_slots + 1)]
    slots_xyxy = [_xyxy_for_area(data, s, bot_id) for s in slots]

    excluded = set()
    for img in exclude_images:
        img = _normalize_png(img)

        try:
            hits = _wait_until_hits(img, inventory_area, bot_id, timeout, interval, max_hits=50)
        except FileNotFoundError:
            log(verbose, f"⚠️ Exclude image niet gevonden, skip: {img}", trace, depth=trace_depth)
            continue

        for h in hits:
            sidx = _hit_to_slot_index(h, slots_xyxy)
            if sidx:
                excluded.add(sidx)

    return excluded


# ============================================================
# MAIN
# ============================================================
def inventory_full(
    *,
    bot_id=1,
    bg_ranges=None,
    empty_threshold=EMPTY_BG_PCT_THRESHOLD,

    exclude_slots=None,
    exclude_images=None,

    slot_prefix=SLOT_PREFIX,
    total_slots=TOTAL_SLOTS,
    inventory_area=INVENTORY_AREA,

    timeout=0,
    interval=0.25,

    verbose=True,
    trace=False,
    trace_depth=6,
    debug_grid=True,
):
    bg_ranges = bg_ranges or BG_RANGES
    exclude_slots = set(exclude_slots or EXCLUDE_SLOTS)
    exclude_images = list(exclude_images or EXCLUDE_IMAGES)

    data = _load_areas()
    slots = _slot_names(prefix=slot_prefix, total=total_slots)
    slots_xyxy = [_xyxy_for_area(data, s, bot_id) for s in slots]

    auto_ex = _excluded_slots_from_images(
        bot_id=bot_id,
        inventory_area=inventory_area,
        slot_prefix=slot_prefix,
        total_slots=total_slots,
        exclude_images=exclude_images,
        timeout=timeout,
        interval=interval,
        verbose=verbose,
        trace=trace,
        trace_depth=trace_depth,
    )
    excluded = set(exclude_slots) | set(auto_ex)

    usable = 0
    filled = 0
    icons = []

    for idx, xyxy in enumerate(slots_xyxy, start=1):
        if idx in excluded:
            icons.append("🟦")
            continue

        usable += 1

        x1, y1, x2, y2 = xyxy
        bgr = _grab_bgr(x1, y1, x2, y2)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        pct = _bg_pct(hsv, bg_ranges)

        empty = pct >= float(empty_threshold)
        if empty:
            icons.append("🟩")
        else:
            icons.append("🟥")
            filled += 1

    full = usable > 0 and filled == usable

    if debug_grid:
        log(verbose, "🧪 Inventory (🟩 Empty | 🟥 Filled | 🟦 Excluded)", trace, depth=trace_depth)
        # OSRS inventory is 4 cols x 7 rows
        for r in range(7):
            row = icons[r * 4 : (r + 1) * 4]
            log(verbose, " ".join(row), trace, depth=trace_depth)

    log(verbose, f"🎒 Inventory full | Filled={filled}/{usable} | Full={full}", trace, depth=trace_depth)
    return full


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    is_full = inventory_full(
        bot_id=1,
        exclude_slots={1},
        exclude_images=["Item_SmallFishingNet.png",],
        timeout=0.0,
        interval=0.25,
        trace=True,
        trace_depth=7,
        debug_grid=True,
    )
    print("VOL ✅" if is_full else "NIET VOL ❌")
