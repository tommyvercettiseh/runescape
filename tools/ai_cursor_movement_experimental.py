from __future__ import annotations

import sys
import time
import random
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pynput.mouse import Controller
from config.areas import load_coords
from core.bot_offsets import apply_offset
from core.ai_cursor import move_cursor
from core.ai_cursor_movement import get_default_bounds, clamp_point, CursorMotionConfig

Point = Tuple[int, int]
Bounds = Tuple[int, int, int, int]


_CTRL = Controller()


def _pick_speed(speed_min: float, speed_max: float, *, slow_chance=0.22, slow_mult=0.60, fast_chance=0.18, fast_mult=1.35) -> float:
    sp = random.uniform(float(speed_min), float(speed_max))
    r = random.random()
    if r < float(slow_chance):
        sp *= float(slow_mult)
    elif r > 1.0 - float(fast_chance):
        sp *= float(fast_mult)
    return max(20.0, min(sp, 240.0))


def _overshoot_target(start: Point, target: Point, bounds: Bounds, *, chance=0.20, min_px=6, max_px=22) -> Point | None:
    if random.random() > float(chance):
        return None
    x1, y1 = start
    x2, y2 = target
    dx = x2 - x1
    dy = y2 - y1
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 20:
        return None
    k = random.uniform(float(min_px), float(max_px)) / max(1.0, dist)
    ox = int(round(x2 + dx * k))
    oy = int(round(y2 + dy * k))
    return clamp_point((ox, oy), bounds)


def _micro_nudge(pos: Point, bounds: Bounds, *, min_px=1, max_px=3) -> Point:
    dx = random.randint(int(min_px), int(max_px)) * (1 if random.random() < 0.5 else -1)
    dy = random.randint(int(min_px), int(max_px)) * (1 if random.random() < 0.5 else -1)
    return clamp_point((pos[0] + dx, pos[1] + dy), bounds)


def experimental_move_cursor(
    target: Point,
    *,
    bounds: Bounds | None = None,
    speed_min=70.0,
    speed_max=165.0,
    overshoot_chance=0.22,
    micro_pause_chance=0.35,
    tremor_chance=0.35,
    tremor_px_min=1,
    tremor_px_max=4,
) -> Point:
    if bounds is None:
        bounds = get_default_bounds()

    start = clamp_point(_CTRL.position, bounds)

    # Overshoot BEFORE target (more human)
    os_target = _overshoot_target(start, target, bounds, chance=overshoot_chance)
    if os_target is not None:
        sp_os = _pick_speed(speed_min * 0.9, speed_max * 0.95)
        move_cursor(os_target, bounds=bounds, speed_pct=sp_os, config=CursorMotionConfig())
        if random.random() < 0.65:
            time.sleep(random.uniform(0.010, 0.055))

    # Main move to target
    sp = _pick_speed(speed_min, speed_max)
    move_cursor(target, bounds=bounds, speed_pct=sp, config=CursorMotionConfig())

    # Micro hesitation near target
    if random.random() < float(micro_pause_chance):
        time.sleep(random.uniform(0.008, 0.060))

    # Tiny hand tremor / micro-adjusts (short nudges, not smooth curves)
    if random.random() < float(tremor_chance):
        tremor_steps = random.randint(1, 3)
        for _ in range(tremor_steps):
            nx, ny = _micro_nudge(target, bounds, min_px=tremor_px_min, max_px=tremor_px_max)
            _CTRL.position = (int(nx), int(ny))
            time.sleep(random.uniform(0.006, 0.030))
        _CTRL.position = (int(target[0]), int(target[1]))

    # Final soft settle on exact target (non-snappy, low speed)
    move_cursor(target, bounds=bounds, speed_pct=_pick_speed(45, 85), config=CursorMotionConfig())

    return clamp_point(target, bounds)


def experimental_random_mouse_movements(
    min_sec,
    max_sec,
    area_name,
    *,
    bot_id=1,
    padding=6,
    speed_min=70.0,
    speed_max=165.0,
    verbose=False,
) -> bool:
    try:
        coords = list(load_coords(area_name))
    except Exception:
        if verbose:
            print(f"❌ exp_mouse: area '{area_name}' niet gevonden via load_coords()")
        return False

    x1, y1, x2, y2 = apply_offset(coords, int(bot_id))
    pad = max(0, int(padding))
    left = int(x1 + pad)
    top = int(y1 + pad)
    right = int(x2 - pad - 1)
    bottom = int(y2 - pad - 1)

    if right <= left or bottom <= top:
        if verbose:
            print("❌ exp_mouse: area te klein na padding")
        return False

    bounds = (left, top, right + 1, bottom + 1)
    total = random.uniform(float(min_sec), float(max_sec))
    end_t = time.time() + total

    if verbose:
        print(f"🌀 EXP mouse movement '{area_name}' bot={bot_id} ~{total:.2f}s")

    # enter area first to avoid clamp jumps
    entry_x = random.randint(left, right)
    entry_y = random.randint(top, bottom)
    move_cursor((entry_x, entry_y), bounds=None, speed_pct=_pick_speed(80, 140), config=CursorMotionConfig())
    time.sleep(random.uniform(0.03, 0.12))

    moves = 0
    while time.time() < end_t:
        tx = random.randint(left, right)
        ty = random.randint(top, bottom)
        experimental_move_cursor(
            (tx, ty),
            bounds=bounds,
            speed_min=speed_min,
            speed_max=speed_max,
        )
        moves += 1
        if random.random() < 0.85:
            time.sleep(random.uniform(0.01, 0.08))

    if verbose:
        print(f"✅ exp_mouse done ({moves} moves)")
    return True
