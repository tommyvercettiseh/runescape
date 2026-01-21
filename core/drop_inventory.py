from __future__ import annotations

import sys
import json
import time
import random
from pathlib import Path

import numpy as np
import cv2

try:
    import mss
except ImportError:
    raise SystemExit("pip install mss")

from pynput.keyboard import Key, Controller

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bot_offsets import get_offset
from core.ai_cursor import move_and_click
from vision.image_detection import detect_images
from helpers.ops import wait_until
from helpers.log import log


# =========================
# CONFIG (pas dit aan)
# =========================
BG_RANGES = [((8, 38, 44), (21, 87, 100))]
EMPTY_BG_PCT_THRESHOLD = 0.90  # >= 90% = leeg (🟩)

EXCLUDE_SLOTS = set()          # bv {1, 28}
EXCLUDE_IMAGES = []            # bv ["Item_Tinderbox.png", "Item_Axe.png"]

SLOT_PREFIX = "Inventory_Slot_"
TOTAL_SLOTS = 28
GRID_COLS = 4
GRID_ROWS = 7

INVENTORY_AREA = "Inventory_Area"

FOCUS_AREA = "Chat_Area"       # ✅ focus click hier (pas aan als je wil)
SHIFT_PRESS_DELAY = 0.10       # ✅ meer marge zodat shift zeker “pakt”
SHIFT_REFRESH_EVERY = 8        # ✅ soms verliest Windows focus/shift, refresh af en toe
SHIFT_REFRESH_DELAY = 0.02

CLICK_PAD_PX = 6               # ✅ klik niet exact op rand/center
STABLE_CLICK_DELAY = 0.0       # ✅ geen extra delay in click itself
STABLE_CLICK_HOLD_MIN = 0.006  # ✅ kort vasthouden voorkomt drag
STABLE_CLICK_HOLD_MAX = 0.014


# =========================
# KEYBOARD (ai_keyboard)
# =========================
def _get_keyboard_controller():
    try:
        from core.ai_keyboard import keyboard as kb  # type: ignore
        return kb
    except Exception:
        return Controller()


# =========================
# HELPERS
# =========================
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
    return (x1 + ox, y1 + oy, x2 + ox, y2 + oy)


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


def _slot_center(x1, y1, x2, y2):
    return (int((x1 + x2) / 2), int((y1 + y2) / 2))


def _rand_point_in_xyxy(x1, y1, x2, y2, pad=CLICK_PAD_PX):
    x1i, y1i, x2i, y2i = int(x1), int(y1), int(x2), int(y2)
    pad = max(0, int(pad))
    xa = x1i + pad
    ya = y1i + pad
    xb = x2i - pad
    yb = y2i - pad
    if xb <= xa:
        xa, xb = x1i, x2i
    if yb <= ya:
        ya, yb = y1i, y2i
    return (random.randint(xa, xb), random.randint(ya, yb))


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


def focus_client(*, bot_id: int, area_name: str = FOCUS_AREA, delay_s: float = 0.10):
    data = _load_areas()
    x1, y1, x2, y2 = _xyxy_for_area(data, area_name, bot_id)
    cx, cy = _slot_center(x1, y1, x2, y2)

    try:
        from core.ai_cursor import ClickConfig, SettleConfig  # type: ignore
        move_and_click(
            (cx, cy),
            button="left",
            click_cfg=ClickConfig(
                delay=STABLE_CLICK_DELAY,
                button="left",
                mode="safe_tap",
                tap_min_s=STABLE_CLICK_HOLD_MIN,
                tap_max_s=STABLE_CLICK_HOLD_MAX,
                lock_pos=True,
            ),
            settle=SettleConfig(chance=0.0),
            rand_cfg=None,
        )
    except Exception:
        move_and_click((cx, cy), button="left")

    time.sleep(float(delay_s))


def stable_click(xy, *, button="left"):
    try:
        from core.ai_cursor import ClickConfig, SettleConfig  # type: ignore
        move_and_click(
            (int(xy[0]), int(xy[1])),
            button=button,
            click_cfg=ClickConfig(
                delay=STABLE_CLICK_DELAY,
                button=button,
                mode="safe_tap",
                tap_min_s=STABLE_CLICK_HOLD_MIN,
                tap_max_s=STABLE_CLICK_HOLD_MAX,
                lock_pos=True,
            ),
            settle=SettleConfig(chance=0.0),
            rand_cfg=None,
        )
    except Exception:
        move_and_click((int(xy[0]), int(xy[1])), button=button)


def refresh_shift(keyboard):
    keyboard.release(Key.shift)
    time.sleep(float(SHIFT_REFRESH_DELAY))
    keyboard.press(Key.shift)
    time.sleep(0.03)


# =========================
# MAIN
# =========================
def drop_inventory(
    *,
    bot_id=1,
    dry_run=True,
    click_delay=0.02,

    use_shift_drop=True,

    skip_chance=0.08,
    max_consecutive_skips=2,
    seed=None,

    bg_ranges=None,
    empty_threshold=EMPTY_BG_PCT_THRESHOLD,

    exclude_slots=None,
    exclude_images=None,

    slot_prefix=SLOT_PREFIX,
    total_slots=TOTAL_SLOTS,
    inventory_area=INVENTORY_AREA,

    grid_cols=GRID_COLS,
    grid_rows=GRID_ROWS,
    debug_grid=True,

    timeout=0,
    interval=0.25,

    verbose=True,
    trace=False,
    trace_depth=6,
    debug=True,
):
    if seed is not None:
        random.seed(seed)

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

    if debug and excluded:
        log(verbose, f"🧷 Excluded slots: {sorted(excluded)}", trace, depth=trace_depth)

    states = []
    for idx, xyxy in enumerate(slots_xyxy, start=1):
        x1, y1, x2, y2 = xyxy
        bgr = _grab_bgr(x1, y1, x2, y2)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        pct = _bg_pct(hsv, bg_ranges)

        empty = pct >= float(empty_threshold)
        is_ex = idx in excluded

        if is_ex:
            icon = "🟦"
        else:
            icon = "🟩" if empty else "🟥"

        states.append((idx, icon, pct, empty, is_ex))

    if debug_grid:
        log(verbose, "🧪 Inventory grid (🟩 empty | 🟥 drop | 🟦 excluded)", trace, depth=trace_depth)
        for r in range(grid_rows):
            icons = []
            pcts = []
            for c in range(grid_cols):
                i = r * grid_cols + c
                _, icon, pct, _, _ = states[i]
                icons.append(icon)
                pcts.append(f"{pct*100:5.1f}")
            log(verbose, f"{' '.join(icons)}    {' '.join(pcts)}", trace, depth=trace_depth)

    dropped = []
    skipped = 0
    consec_skips = 0

    keyboard = _get_keyboard_controller()

    if use_shift_drop and not dry_run:
        focus_client(bot_id=bot_id, area_name=FOCUS_AREA, delay_s=0.10)
        keyboard.press(Key.shift)
        time.sleep(float(SHIFT_PRESS_DELAY))

    try:
        for idx, icon, pct, empty, is_ex in states:
            if is_ex or empty:
                continue

            do_skip = (random.random() < float(skip_chance)) and (consec_skips < int(max_consecutive_skips))
            if do_skip:
                skipped += 1
                consec_skips += 1
                debug and log(
                    verbose,
                    f"🙈 Skipped drop | Slot={idx} | Consecutive={consec_skips}",
                    trace,
                    depth=trace_depth,
                )
                continue

            consec_skips = 0

            if use_shift_drop and not dry_run and SHIFT_REFRESH_EVERY and (idx % int(SHIFT_REFRESH_EVERY) == 0):
                refresh_shift(keyboard)

            x1, y1, x2, y2 = slots_xyxy[idx - 1]
            cx, cy = _rand_point_in_xyxy(x1, y1, x2, y2, pad=CLICK_PAD_PX)

            debug and log(
                verbose,
                f"🧹 {'Shift-' if use_shift_drop else ''}drop slot {idx} | BG={pct*100:.1f}% @({cx},{cy})",
                trace,
                depth=trace_depth,
            )

            if not dry_run:
                stable_click((cx, cy), button="left")
                time.sleep(float(click_delay))

            dropped.append(idx)

    finally:
        if use_shift_drop and not dry_run:
            keyboard.release(Key.shift)
            time.sleep(0.02)

    debug and log(
        verbose,
        f"📊 Dropped={len(dropped)} | Skipped={skipped} | Skip%={skip_chance*100:.1f}% | MaxConsec={max_consecutive_skips}",
        trace,
        depth=trace_depth,
    )

    log(verbose, f"✅ Dropped slots: {dropped if dropped else '(none)'}", trace, depth=trace_depth)
    return dropped


if __name__ == "__main__":
    drop_inventory(
        bot_id=1,
        dry_run=False,
        click_delay=0.02,

        use_shift_drop=True,

        skip_chance=0.09,
        max_consecutive_skips=2,
        seed=None,

        bg_ranges=BG_RANGES,
        empty_threshold=0.90,

        exclude_slots={1},
        exclude_images=["Item_Tinderbox.png", "Item_Axe.png"],

        debug_grid=True,
        trace=True,
        trace_depth=7,
        debug=True,

        timeout=1.0,
        interval=0.25,
    )
