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
from typing import Tuple, List, Callable

from config.areas import load_coords
from core.bot_offsets import apply_offset

Point = Tuple[int, int]
Bounds = Tuple[int, int, int, int]

"""
Motion tuning notes:
- Humans do not move with constant speed.
- Humans do short pauses (micro and long).
- Humans drift and overshoot sometimes.
- Humans have tremor and small correction behavior.
"""

# ============================================================
# TUNING CONSTANTS (can be overridden by profile)
# ============================================================
TICK_MIN = 0.006
TICK_MAX = 0.015
TICK_JITTER = 0.15
TICK_OUTLIER_CHANCE = 0.010
TICK_LONG_MIN = 0.014
TICK_LONG_MAX = 0.052

STEP_MICRO_PAUSE_CHANCE = 0.006
STEP_MICRO_PAUSE_MIN = 0.006
STEP_MICRO_PAUSE_MAX = 0.020
STEP_LONG_PAUSE_CHANCE = 0.0012
STEP_LONG_PAUSE_MIN = 0.060
STEP_LONG_PAUSE_MAX = 0.150

SPEED_MIN_PX_S = 700
SPEED_MAX_PX_S = 1500
SPEED_JITTER = 0.10

SLOW_CHANCE = 0.30
SLOW_MULT = 0.80

MAX_STEP_PX = 26

BEND_MAX = 55.0
BEND_FACTOR = 0.10

DRIFT_SCALE = 0.0007
DRIFT_MIN = 0.08
DRIFT_MAX = 1.35
DRIFT_FREQ_MIN = 0.80
DRIFT_FREQ_MAX = 2.20
TANGENT_DRIFT_SCALE = 0.0004
TANGENT_DRIFT_MIN = 0.03
TANGENT_DRIFT_MAX = 0.80
TANGENT_FREQ_MIN = 1.10
TANGENT_FREQ_MAX = 3.20
MICRO_TREMOR_MAX = 0.22

OVERSHOOT_CHANCE = 0.24
OVERSHOOT_MIN_PX = 4.0
OVERSHOOT_MAX_PX = 22.0

# ============================================================
# PROFILE TUNING (from core.ai_cursor_settings.mouse_profile)
# ============================================================
def apply_profile_tuning(t: dict) -> None:
    """Apply profile tuning to movement-level globals.
    Expected keys (all optional):
      speed_min, speed_max, overshoot_min, overshoot_max,
      drift_scale, micro_tremor_max, step_micro_pause_chance, step_long_pause_chance
    """
    global SPEED_MIN_PX_S, SPEED_MAX_PX_S
    global OVERSHOOT_MIN_PX, OVERSHOOT_MAX_PX
    global DRIFT_SCALE, MICRO_TREMOR_MAX
    global STEP_MICRO_PAUSE_CHANCE, STEP_LONG_PAUSE_CHANCE

    if not isinstance(t, dict) or not t:
        return

    def f(key, default=None):
        if key not in t:
            return default
        try:
            return float(t[key])
        except Exception:
            return default

    vmin = f("speed_min")
    vmax = f("speed_max")
    if vmin is not None:
        SPEED_MIN_PX_S = int(max(150, vmin))
    if vmax is not None:
        SPEED_MAX_PX_S = int(max(SPEED_MIN_PX_S + 50, vmax))

    omin = f("overshoot_min")
    omax = f("overshoot_max")
    if omin is not None:
        OVERSHOOT_MIN_PX = float(max(1.0, omin))
    if omax is not None:
        OVERSHOOT_MAX_PX = float(max(OVERSHOOT_MIN_PX + 1.0, omax))

    ds = f("drift_scale")
    if ds is not None:
        DRIFT_SCALE = float(max(0.0, ds))

    mt = f("micro_tremor_max")
    if mt is not None:
        MICRO_TREMOR_MAX = float(max(0.0, mt))

    smp = f("step_micro_pause_chance")
    if smp is not None:
        STEP_MICRO_PAUSE_CHANCE = float(max(0.0, min(0.20, smp)))

    slp = f("step_long_pause_chance")
    if slp is not None:
        STEP_LONG_PAUSE_CHANCE = float(max(0.0, min(0.10, slp)))


def _auto_apply_profile() -> None:
    try:
        from core.ai_cursor_settings import mouse_profile as _MP
        if isinstance(_MP, dict) and _MP:
            apply_profile_tuning(_MP)
    except Exception:
        pass


_auto_apply_profile()
# ============================================================


@dataclass(frozen=True)
class CursorMotionConfig:
    duration: float = 0.35
    fps: int = 100
    min_duration: float = 0.08
    min_steps: int = 12


@dataclass(frozen=True)
class PlannedStep:
    x: int
    y: int
    dt: float
    tremor: float = 0.0


def clamp_point(p: Point, b: Bounds) -> Point:
    x0, y0, x1, y1 = b
    return (max(x0, min(x1, int(p[0]))), max(y0, min(y1, int(p[1]))))


def get_default_bounds() -> Bounds:
    return (0, 0, 1919, 1079)


def _dist(a: Point, b: Point) -> float:
    return ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5


def _tick() -> float:
    t = random.uniform(TICK_MIN, TICK_MAX)
    if random.random() < TICK_OUTLIER_CHANCE:
        t = random.uniform(TICK_LONG_MIN, TICK_LONG_MAX)
    t *= random.uniform(1.0 - TICK_JITTER, 1.0 + TICK_JITTER)
    return max(0.001, t)


def _maybe_pause():
    r = random.random()
    if r < STEP_MICRO_PAUSE_CHANCE:
        time.sleep(random.uniform(STEP_MICRO_PAUSE_MIN, STEP_MICRO_PAUSE_MAX))
    elif r < STEP_MICRO_PAUSE_CHANCE + STEP_LONG_PAUSE_CHANCE:
        time.sleep(random.uniform(STEP_LONG_PAUSE_MIN, STEP_LONG_PAUSE_MAX))


def _speed_px_s() -> float:
    base = random.uniform(SPEED_MIN_PX_S, SPEED_MAX_PX_S)
    base *= random.uniform(1.0 - SPEED_JITTER, 1.0 + SPEED_JITTER)
    if random.random() < SLOW_CHANCE:
        base *= SLOW_MULT
    return max(120.0, base)


def _ease(t: float) -> float:
    # smoothstep
    return t * t * (3.0 - 2.0 * t)


def _bend_point(a: Point, b: Point, bounds: Bounds, min_px: float, max_px: float) -> Point:
    mx = (a[0] + b[0]) / 2.0
    my = (a[1] + b[1]) / 2.0
    ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2.0
    mag = random.uniform(min_px, max_px)
    mx += math.cos(ang) * mag
    my += math.sin(ang) * mag
    return clamp_point((int(mx), int(my)), bounds)


def _drift(i: int, total: int) -> Tuple[float, float]:
    if total <= 1:
        return (0.0, 0.0)
    t = i / (total - 1)
    amp = random.uniform(DRIFT_MIN, DRIFT_MAX) * (1.0 + (t * 0.35))
    freq = random.uniform(DRIFT_FREQ_MIN, DRIFT_FREQ_MAX)
    dx = math.sin(t * math.tau * freq) * amp * DRIFT_SCALE * 1000.0
    dy = math.cos(t * math.tau * freq) * amp * DRIFT_SCALE * 1000.0

    amp2 = random.uniform(TANGENT_DRIFT_MIN, TANGENT_DRIFT_MAX)
    freq2 = random.uniform(TANGENT_FREQ_MIN, TANGENT_FREQ_MAX)
    dx += math.sin(t * math.tau * freq2 + 1.1) * amp2 * TANGENT_DRIFT_SCALE * 1000.0
    dy += math.cos(t * math.tau * freq2 + 0.6) * amp2 * TANGENT_DRIFT_SCALE * 1000.0
    return (dx, dy)


def _tremor() -> float:
    return random.uniform(0.0, MICRO_TREMOR_MAX)


def _overshoot_target(start: Point, target: Point, bounds: Bounds) -> Point:
    dx = target[0] - start[0]
    dy = target[1] - start[1]
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 1.0:
        return target
    ux, uy = dx / dist, dy / dist
    over = random.uniform(OVERSHOOT_MIN_PX, OVERSHOOT_MAX_PX)
    tx = int(target[0] + ux * over)
    ty = int(target[1] + uy * over)
    return clamp_point((tx, ty), bounds)


def plan_move(
    start: Point,
    target: Point,
    *,
    config: CursorMotionConfig = CursorMotionConfig(),
    bounds: Bounds | None = None,
    speed_pct: float = 100.0,
) -> List[PlannedStep]:
    if bounds is None:
        bounds = get_default_bounds()

    start = clamp_point(start, bounds)
    target = clamp_point(target, bounds)

    dist = _dist(start, target)
    if dist < 0.5:
        return []

    # overshoot sometimes (handled by caller too, but keep fallback here)
    if dist > 18 and random.random() < OVERSHOOT_CHANCE:
        through = _overshoot_target(start, target, bounds)
        steps = plan_move(start, through, config=config, bounds=bounds, speed_pct=speed_pct)
        steps += plan_move(through, target, config=config, bounds=bounds, speed_pct=speed_pct)
        return steps

    # base duration from distance and speed
    speed = _speed_px_s() * (max(10.0, float(speed_pct)) / 100.0)
    duration = max(config.min_duration, min(config.duration * 2.2, dist / max(1.0, speed)))

    # bend for longer moves
    a = start
    b = target
    if dist > 120 and random.random() < BEND_FACTOR:
        mid = _bend_point(a, b, bounds, min_px=8, max_px=min(BEND_MAX, dist * 0.22))
        return plan_move(a, mid, config=config, bounds=bounds, speed_pct=speed_pct) + plan_move(
            mid, b, config=config, bounds=bounds, speed_pct=speed_pct
        )

    fps = max(30, int(config.fps))
    total_steps = max(config.min_steps, int(duration * fps))
    total_steps = max(6, total_steps)

    # step size cap
    if dist / total_steps > MAX_STEP_PX:
        total_steps = int(math.ceil(dist / MAX_STEP_PX))

    steps: List[PlannedStep] = []
    for i in range(total_steps):
        t = i / (total_steps - 1) if total_steps > 1 else 1.0
        e = _ease(t)
        dx, dy = _drift(i, total_steps)
        x = int(round(a[0] + (b[0] - a[0]) * e + dx))
        y = int(round(a[1] + (b[1] - a[1]) * e + dy))
        x, y = clamp_point((x, y), bounds)
        steps.append(PlannedStep(x=x, y=y, dt=_tick(), tremor=_tremor()))
    return steps