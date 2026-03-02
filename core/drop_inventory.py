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

# ============================================================
# BOOTSTRAP (start anywhere)
# zoekt project root met /core en /config
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
from core.ai_mouse.ai_mouse import human_move_to, human_click

from core.ai_keyboard.ai_keyboard_executor import KeyboardExecutor, resolve_key
from core.ai_keyboard.ai_keyboard_settings import get_keyboard_config

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

FOCUS_AREA = "Chat_Area"       # focus click hier (pas aan als je wil)

CLICK_PAD_PX = 6               # klik niet exact op rand

# =========================
# PATTERN CONFIG
# =========================
PATTERNS = ("E", "3", "W", "N")
AUTO_PATTERN = "AUTO"


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

    human_move_to(cx, cy)
    human_click(mode="safe_tap")

    time.sleep(float(delay_s))


def stable_click(xy, *, button="left"):
    x, y = int(xy[0]), int(xy[1])
    human_move_to(x, y)
    human_click(button=button, mode="safe_tap")


def _human_click_delay(min_s: float, max_s: float, jitter: float = 0.0) -> float:
    a = float(min_s)
    b = float(max_s)
    if b < a:
        a, b = b, a

    base = random.uniform(a, b)
    if jitter and float(jitter) > 0:
        base += random.uniform(-float(jitter), float(jitter))

    return max(0.0, float(base))


def build_slot_order(
    pattern="E",
    *,
    total_slots=28,
    grid_cols=4,
    grid_rows=7,
    seed=None,
):
    p = (pattern or "E").strip().upper()

    if seed is not None:
        random.seed(seed)

    def rc_to_idx(r, c):
        return r * grid_cols + c + 1

    max_cells = grid_cols * grid_rows
    if total_slots > max_cells:
        total_slots = max_cells

    order = []

    if p == "E":
        for r in range(grid_rows):
            for c in range(grid_cols):
                idx = rc_to_idx(r, c)
                if idx <= total_slots:
                    order.append(idx)

    elif p == "3":
        for r in range(grid_rows):
            for c in range(grid_cols - 1, -1, -1):
                idx = rc_to_idx(r, c)
                if idx <= total_slots:
                    order.append(idx)

    elif p == "W":
        for r in range(grid_rows):
            cols = range(grid_cols) if (r % 2 == 0) else range(grid_cols - 1, -1, -1)
            for c in cols:
                idx = rc_to_idx(r, c)
                if idx <= total_slots:
                    order.append(idx)

    elif p == "N":
        for c in range(grid_cols):
            rows = range(grid_rows) if (c % 2 == 0) else range(grid_rows - 1, -1, -1)
            for r in rows:
                idx = rc_to_idx(r, c)
                if idx <= total_slots:
                    order.append(idx)

    elif p == "R":
        order = list(range(1, total_slots + 1))
        random.shuffle(order)

    else:
        order = list(range(1, total_slots + 1))

    return order


def _resolve_pattern(pattern, *, allow_random=True):
    p = (pattern or "").strip().upper()
    if not p or p == AUTO_PATTERN:
        return random.choice(PATTERNS) if allow_random else "E"
    if p in PATTERNS:
        return p
    if p == "R":
        return "R"
    return "E"


# ============================================================
# SHIFT HOLD (ai_keyboard timing)
# ============================================================
def _shift_hold_start(ex: KeyboardExecutor, *, scenario_label: str | None = "shift_hold") -> None:
    cfg = get_keyboard_config(scenario_label).behavior
    k = resolve_key("shift")
    ex.press(k)
    time.sleep(random.uniform(float(cfg.press_min_s), float(cfg.press_max_s)))


def _shift_hold_end(ex: KeyboardExecutor, *, scenario_label: str | None = "shift_hold") -> None:
    cfg = get_keyboard_config(scenario_label).behavior
    k = resolve_key("shift")
    time.sleep(random.uniform(float(cfg.press_min_s) * 0.5, float(cfg.press_max_s) * 0.9))
    ex.release(k)


# =========================
# MAIN
# =========================
def drop_inventory(
    *,
    bot_id=1,
    dry_run=False,

    # BACKWARDS COMPAT (als je dit meegeeft -> fixed delay)
    click_delay=None,

    # NIEUW (variabele delay)
    click_delay_min=0.08,
    click_delay_max=0.18,
    click_delay_jitter=0.015,

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

    pattern=AUTO_PATTERN,
    pattern_seed=None,
    allow_random_pattern=True,

    # timing label voor ai_keyboard
    shift_scenario_label="shift_hold",
):
    if seed is not None:
        random.seed(seed)

    bg_ranges = bg_ranges or BG_RANGES
    exclude_slots = set(exclude_slots or EXCLUDE_SLOTS)
    exclude_images = list(exclude_images or EXCLUDE_IMAGES)

    chosen_pattern = _resolve_pattern(pattern, allow_random=allow_random_pattern)
    if debug:
        log(verbose, f"🧩 Pattern: {chosen_pattern}", trace, depth=trace_depth)

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
        log(verbose, "🧪 Inventory grid (🟩 empty | 🟥 action | 🟦 excluded)", trace, depth=trace_depth)
        for r in range(grid_rows):
            icons = []
            pcts = []
            for c in range(grid_cols):
                i = r * grid_cols + c
                if i >= len(states):
                    continue
                _, icon, pct, _, _ = states[i]
                icons.append(icon)
                pcts.append(f"{pct*100:5.1f}")
            log(verbose, f"{' '.join(icons)}    {' '.join(pcts)}", trace, depth=trace_depth)

    dropped = []
    skipped = 0
    consec_skips = 0

    # 1 executor voor de hele run (stabiel)
    kb_ex = KeyboardExecutor()

    try:
        # SHIFT CONTINUE HOLD ✅
        if use_shift_drop and not dry_run:
            focus_client(bot_id=bot_id, area_name=FOCUS_AREA, delay_s=0.10)
            _shift_hold_start(kb_ex, scenario_label=shift_scenario_label)

        order_seed = pattern_seed if (chosen_pattern == "R") else None
        order = build_slot_order(
            chosen_pattern,
            total_slots=total_slots,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
            seed=order_seed,
        )

        for idx in order:
            i = idx - 1
            if i < 0 or i >= len(states):
                continue

            _, _, pct, empty, is_ex = states[i]

            if is_ex or empty:
                continue

            do_skip = (random.random() < float(skip_chance)) and (consec_skips < int(max_consecutive_skips))
            if do_skip:
                skipped += 1
                consec_skips += 1
                if debug:
                    log(verbose, f"🙈 Skipped action | Slot={idx} | Consecutive={consec_skips}", trace, depth=trace_depth)
                continue

            consec_skips = 0

            x1, y1, x2, y2 = slots_xyxy[i]
            cx, cy = _rand_point_in_xyxy(x1, y1, x2, y2, pad=CLICK_PAD_PX)

            if click_delay is not None:
                delay = float(click_delay)
            else:
                delay = _human_click_delay(click_delay_min, click_delay_max, click_delay_jitter)

            if debug:
                log(
                    verbose,
                    f"🧹 {'Shift-' if use_shift_drop else ''}action slot {idx} | BG={pct*100:.1f}% @({cx},{cy}) | Delay={delay:.3f}s",
                    trace,
                    depth=trace_depth,
                )

            if not dry_run:
                stable_click((cx, cy), button="left")
                time.sleep(delay)

            dropped.append(idx)

    finally:
        if use_shift_drop and not dry_run:
            _shift_hold_end(kb_ex, scenario_label=shift_scenario_label)

    if debug:
        log(
            verbose,
            f"📊 Done={len(dropped)} | Skipped={skipped} | Skip%={skip_chance*100:.1f}% | MaxConsec={max_consecutive_skips}",
            trace,
            depth=trace_depth,
        )

    log(verbose, f"✅ Done slots: {dropped if dropped else '(none)'}", trace, depth=trace_depth)
    return dropped


if __name__ == "__main__":
    drop_inventory(
        bot_id=1,
        dry_run=False,

        click_delay_min=0.09,
        click_delay_max=0.17,
        click_delay_jitter=0.015,

        use_shift_drop=True,

        skip_chance=0.09,
        max_consecutive_skips=2,

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

        pattern="AUTO",
        allow_random_pattern=True,

        shift_scenario_label="shift_hold",
    )