from __future__ import annotations
import time
import random
import math
import ctypes
from dataclasses import dataclass
from typing import Tuple, List

Point = Tuple[int, int]
Bounds = Tuple[int, int, int, int]

# ============================================================
# TWEAKS (zelfde als jij nu hebt)
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
    # vermijd pyautogui hier om planner “clean” te houden
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
) -> List[PlannedStep]:
    """
    Planner: maakt een lijst (x,y,sleep) stappen.
    Geen echte muis acties hier.
    """
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

    # curve control point
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
        planned.append(PlannedStep(x=xi, y=yi, sleep_s=_clamp(_pick_tick(), 0.002, 0.02)))

    # micro-correct als extra stapjes
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
        planned.append(PlannedStep(x=curx, y=cury, sleep_s=_clamp(_pick_tick(), 0.002, 0.02)))

    return planned
