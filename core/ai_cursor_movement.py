from __future__ import annotations

# ============================================================
# BOOTSTRAP
# ============================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .../Runescape
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
import time
import random
import math
import ctypes
import importlib
from dataclasses import dataclass
from typing import Tuple, List

from config.areas import load_coords
from core.bot_offsets import apply_offset

Point = Tuple[int, int]
Bounds = Tuple[int, int, int, int]

# ============================================================
# TWEAKS
# ============================================================
USE_VIRTUAL_BOUNDS = True
MAX_DURATION_PER_MOVE = 1.65

TICK_MIN = 0.006
TICK_MAX = 0.011

SPEED_MIN_PX_S = 700
SPEED_MAX_PX_S = 1500
SPEED_JITTER = 0.10

SLOW_CHANCE = 0.30
SLOW_MULT = 0.80

MAX_STEP_PX = 26

BEND_MAX = 55.0
BEND_FACTOR = 0.10

DRIFT_SCALE = 0.0012
DRIFT_MIN = 0.08
DRIFT_MAX = 0.95
DRIFT_FREQ_MIN = 0.95
DRIFT_FREQ_MAX = 1.25
# ============================================================


@dataclass(frozen=True)
class CursorMotionConfig:
    duration: float = 0.35
    fps: int = 120
    min_duration: float = 0.08
    min_steps: int = 12


@dataclass(frozen=True)
class PlannedStep:
    x: int
    y: int
    sleep_s: float


def _ease_in_out_quad(t: float) -> float:
    return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _scale_sleep(sleep_s: float, speed_pct: float) -> float:
    try:
        sp = float(speed_pct)
    except Exception:
        sp = 100.0

    if sp <= 0:
        sp = 1.0

    factor = 100.0 / sp
    return float(sleep_s) * factor


def get_virtual_screen_bounds() -> Bounds:
    user32 = ctypes.windll.user32
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    x1 = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    y1 = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    w = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    h = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
    return (x1, y1, x1 + w, y1 + h)


def get_primary_bounds() -> Bounds:
    user32 = ctypes.windll.user32
    w = int(user32.GetSystemMetrics(0))
    h = int(user32.GetSystemMetrics(1))
    return (0, 0, w, h)


def get_default_bounds() -> Bounds:
    return get_virtual_screen_bounds() if USE_VIRTUAL_BOUNDS else get_primary_bounds()


def clamp_point(p: Point, bounds: Bounds) -> Point:
    x, y = int(p[0]), int(p[1])
    x1, y1, x2, y2 = bounds
    x = max(x1, min(x, x2 - 1))
    y = max(y1, min(y, y2 - 1))
    return (x, y)


def _bezier2(p0: Point, p1: Tuple[float, float], p2: Point, t: float) -> Tuple[float, float]:
    inv = 1.0 - t
    x = inv * inv * p0[0] + 2 * inv * t * p1[0] + t * t * p2[0]
    y = inv * inv * p0[1] + 2 * inv * t * p1[1] + t * t * p2[1]
    return x, y


def _pick_tick() -> float:
    return random.uniform(TICK_MIN, TICK_MAX)


def _speed_for_dist(dist: float) -> float:
    k = 1.0 - math.exp(-dist / 550.0)
    speed = SPEED_MIN_PX_S + (SPEED_MAX_PX_S - SPEED_MIN_PX_S) * k
    speed *= random.uniform(1.0 - SPEED_JITTER, 1.0 + SPEED_JITTER)
    if random.random() < SLOW_CHANCE:
        speed *= SLOW_MULT
    return max(250.0, speed)


def plan_move(
    start_pos: Point,
    target_pos: Point,
    *,
    config: CursorMotionConfig = CursorMotionConfig(),
    bounds: Bounds | None = None,
    speed_pct: float = 100.0,
) -> List[PlannedStep]:
    if bounds is None:
        bounds = get_default_bounds()

    x2, y2 = clamp_point(target_pos, bounds)
    x1, y1 = clamp_point(start_pos, bounds)

    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)

    if dist <= 1.0:
        return [PlannedStep(x=x2, y=y2, sleep_s=0.0)]

    speed = _speed_for_dist(dist)
    duration = dist / speed
    duration = _clamp(duration, float(config.min_duration), float(MAX_DURATION_PER_MOVE))

    tick = _pick_tick()
    steps = max(int(duration / tick), int(config.min_steps))
    steps = min(steps, int(MAX_DURATION_PER_MOVE / TICK_MIN))

    min_steps_for_cap = int(math.ceil(dist / MAX_STEP_PX))
    steps = max(steps, min_steps_for_cap)

    if dist < 90:
        cx = x1 + dx * 0.5
        cy = y1 + dy * 0.5
    else:
        nxp = -dy / dist
        nyp = dx / dist
        bend = random.uniform(-1.0, 1.0) * min(BEND_MAX, dist * BEND_FACTOR)
        cx = x1 + dx * random.uniform(0.42, 0.58) + nxp * bend
        cy = y1 + dy * random.uniform(0.42, 0.58) + nyp * bend

    p0 = (x1, y1)
    p1 = (cx, cy)
    p2 = (x2, y2)

    nx = -dy / dist
    ny = dx / dist
    amp = _clamp(dist * DRIFT_SCALE, DRIFT_MIN, DRIFT_MAX) * random.uniform(0.85, 1.10)
    phase = random.uniform(0.0, math.tau)
    freq = random.uniform(DRIFT_FREQ_MIN, DRIFT_FREQ_MAX)

    fx, fy = float(x1), float(y1)
    planned: List[PlannedStep] = []

    for i in range(1, steps + 1):
        t = i / steps
        s = _ease_in_out_quad(t)

        tx, ty = _bezier2(p0, p1, p2, s)

        decay = 1.0 - s
        drift = math.sin(phase + s * math.tau * freq) * amp * decay
        tx += nx * drift
        ty += ny * drift

        ddx = tx - fx
        ddy = ty - fy
        step_len = math.hypot(ddx, ddy)

        if step_len > MAX_STEP_PX and step_len > 0.0001:
            k = MAX_STEP_PX / step_len
            fx += ddx * k
            fy += ddy * k
        else:
            fx, fy = tx, ty

        xi, yi = clamp_point((int(round(fx)), int(round(fy))), bounds)
        base_sleep = _clamp(_pick_tick(), 0.002, 0.02)
        planned.append(PlannedStep(x=xi, y=yi, sleep_s=_scale_sleep(base_sleep, speed_pct)))

    curx, cury = planned[-1].x, planned[-1].y
    for _ in range(10):
        ddx = x2 - curx
        ddy = y2 - cury
        r = math.hypot(ddx, ddy)
        if r <= 1.3:
            break
        k = min(1.0, MAX_STEP_PX / max(1.0, r))
        curx = int(curx + ddx * k)
        cury = int(cury + ddy * k)
        curx, cury = clamp_point((curx, cury), bounds)
        base_sleep = _clamp(_pick_tick(), 0.002, 0.02)
        planned.append(PlannedStep(x=curx, y=cury, sleep_s=_scale_sleep(base_sleep, speed_pct)))

    return planned


# ============================================================
# RANDOM MOUSE MOVEMENT (AREA BASED, NO TELEPORT START)
# ============================================================
def random_mouse_movements(
    min_sec,
    max_sec,
    area_name,
    *,
    bot_id=1,
    padding=6,
    verbose=False,

    # ✅ feel settings
    fps=120,                 # fps blijft altijd hetzelfde
    speed_min=65.0,          # % speed range (lager = trager)
    speed_max=165.0,         # % speed range (hoger = sneller)
    slow_chance=0.22,        # kans op "langzaam moment"
    slow_mult=0.55,          # maakt speed tijdelijk lager
    fast_chance=0.18,        # kans op "sneller moment"
    fast_mult=1.35,          # maakt speed tijdelijk hoger

    # ✅ segment timing (wordt nog dynamisch gecorrigeerd)
    seg_min=0.12,
    seg_max=0.70,

    # ✅ pause feel (micro pauses)
    pause_min=0.01,
    pause_max=0.08,

    enter_first=True,
) -> bool:
    """
    Random mouse movement binnen area voor min_sec..max_sec seconden.
    Dynamischer: speed varieert per segment, fps blijft constant, blijft smooth.
    """

    ai = importlib.import_module("core.ai_cursor")
    move_cursor = ai.move_cursor

    try:
        coords = list(load_coords(area_name))
    except Exception:
        if verbose:
            print(f"❌ random_mouse_movement: area '{area_name}' niet gevonden via load_coords()")
        return False

    x1, y1, x2, y2 = apply_offset(coords, int(bot_id))

    pad = max(0, int(padding))
    left = int(x1 + pad)
    top = int(y1 + pad)
    right = int(x2 - pad - 1)
    bottom = int(y2 - pad - 1)

    if right <= left or bottom <= top:
        if verbose:
            print("❌ random_mouse_movement: area te klein na padding")
        return False

    bounds = (left, top, right + 1, bottom + 1)

    total = random.uniform(float(min_sec), float(max_sec))
    end_t = time.time() + total

    if verbose:
        print(f"🌀 Random mouse movement '{area_name}' bot={bot_id} ~{total:.2f}s fps={fps}")

    # ------------------------------------------------------------
    # helpers: dynamische speed & segment durations (smooth)
    # ------------------------------------------------------------
    def _pick_speed():
        sp = random.uniform(float(speed_min), float(speed_max))

        r = random.random()
        if r < float(slow_chance):
            sp *= float(slow_mult)
        elif r > 1.0 - float(fast_chance):
            sp *= float(fast_mult)

        # cap safe
        return max(20.0, min(sp, 240.0))

    def _seg_duration(speed_pct):
        """
        Sneller = kortere duration.
        Trager = langere duration.
        """
        base = random.uniform(float(seg_min), float(seg_max))

        # speed influence (100% ~ neutraal)
        if speed_pct >= 100:
            base *= random.uniform(0.65, 0.95)
        else:
            base *= random.uniform(1.05, 1.55)

        # af en toe een "slow sweep"
        if random.random() < 0.14:
            base *= random.uniform(1.15, 1.90)

        return max(0.10, min(base, 1.25))

    # ------------------------------------------------------------
    # enter area first (voorkomt teleport clamp-start)
    # ------------------------------------------------------------
    if enter_first:
        entry_x = random.randint(left, right)
        entry_y = random.randint(top, bottom)

        entry_speed = _pick_speed()
        entry_dur = max(0.35, _seg_duration(entry_speed))

        entry_motion = CursorMotionConfig(duration=float(entry_dur), fps=int(fps))

        move_cursor(
            (entry_x, entry_y),
            config=entry_motion,
            bounds=None,  # 🔥 belangrijk
            speed_pct=float(entry_speed),
        )

    # ------------------------------------------------------------
    # main wander loop
    # ------------------------------------------------------------
    moves = 0
    while time.time() < end_t:
        remaining = end_t - time.time()
        if remaining <= 0:
            break

        tx = random.randint(left, right)
        ty = random.randint(top, bottom)

        sp = _pick_speed()
        dur = _seg_duration(sp)

        # niet te lang als we bijna klaar zijn
        if remaining < 0.25:
            dur = min(dur, remaining)

        motion = CursorMotionConfig(duration=float(dur), fps=int(fps))

        move_cursor(
            (tx, ty),
            config=motion,
            bounds=bounds,
            speed_pct=float(sp),
        )

        moves += 1

        # micro pause (niet altijd, anders voelt het "scripted")
        if pause_max > 0:
            if random.random() < 0.85:
                time.sleep(random.uniform(float(pause_min), float(pause_max)))

    if verbose:
        print(f"✅ random_mouse_movement done ({moves} moves)")

    return True

# ============================================================
# SELF TEST
# ============================================================
if __name__ == "__main__":
    VERBOSE = True
    ok = random_mouse_movement(1, 4, "Bot_Area_Full", bot_id=1, verbose=VERBOSE)
    print(f"🧪 Test klaar | success={ok}")
