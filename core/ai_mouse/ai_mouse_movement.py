from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional

Point = Tuple[int, int]
Bounds = Tuple[int, int, int, int]


# =========================
# DATA STRUCTS
# =========================

@dataclass
class PlannedStep:
    x: int
    y: int
    dt: float  # seconds


@dataclass
class CursorMotionConfig:
    # speed range (px/s)
    speed_min: float = 800.0
    speed_max: float = 1800.0

    # overshoot range (px)
    overshoot_min: float = 4.0
    overshoot_max: float = 18.0

    # snap radius
    close_px: float = 2.2

    # tick / cadence (seconds per step)
    tick_min: float = 0.007
    tick_max: float = 0.013

    # curvature
    curve_strength: float = 0.22  # 0..1

    # tremor / jitter baseline (px)
    jitter_px: float = 0.25

    # micro pauses
    micro_pause_chance: float = 0.03
    micro_pause_min: float = 0.010
    micro_pause_max: float = 0.045

    # braking near end
    end_slowdown: float = 0.65  # 0..1

    # correction phase
    correction_steps_min: int = 2
    correction_steps_max: int = 7

    # much less jitter in correction
    correction_jitter_scale: float = 0.25


_DEFAULT_CONFIG = CursorMotionConfig()


# =========================
# UTILS
# =========================

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def clamp_point(p: Point, bounds: Bounds) -> Point:
    x1, y1, x2, y2 = bounds
    x = int(_clamp(p[0], x1, x2))
    y = int(_clamp(p[1], y1, y2))
    return x, y

def get_default_bounds() -> Bounds:
    try:
        import pyautogui
        w, h = pyautogui.size()
        return (0, 0, int(w - 1), int(h - 1))
    except Exception:
        return (0, 0, 1919, 1079)

def _dist(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])

def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

def _rand(a: float, b: float) -> float:
    return random.uniform(a, b)

def _ease_in_out(t: float) -> float:
    return (1 - math.cos(math.pi * t)) / 2


# =========================
# PROFILE TUNING
# =========================

def apply_profile_tuning(mouse_profile: dict, cfg: Optional[CursorMotionConfig] = None) -> CursorMotionConfig:
    """
    Keys supported:
      speed_min, speed_max, overshoot_min, overshoot_max, close_px, micro_tremor_max
    """
    global _DEFAULT_CONFIG
    cfg = cfg or CursorMotionConfig()

    def g(k: str, default: float) -> float:
        try:
            return float(mouse_profile.get(k, default))
        except Exception:
            return float(default)

    cfg.speed_min = max(50.0, g("speed_min", cfg.speed_min))
    cfg.speed_max = max(cfg.speed_min + 50.0, g("speed_max", cfg.speed_max))

    cfg.overshoot_min = max(0.0, g("overshoot_min", cfg.overshoot_min))
    cfg.overshoot_max = max(cfg.overshoot_min, g("overshoot_max", cfg.overshoot_max))

    cfg.close_px = max(0.5, g("close_px", cfg.close_px))

    trem = mouse_profile.get("micro_tremor_max", None)
    if trem is not None:
        try:
            trem = float(trem)
            # FIX: micro_tremor is endpoint feel, not whole-path jitter
            cfg.jitter_px = _clamp(trem * 0.85, 0.08, 0.35)
        except Exception:
            pass

    _DEFAULT_CONFIG = cfg
    return cfg


# =========================
# PLANNER
# =========================

def plan_move(
    start: Point,
    target: Point,
    *,
    bounds: Optional[Bounds] = None,
    config: Optional[CursorMotionConfig] = None,
) -> List[PlannedStep]:
    cfg = config or _DEFAULT_CONFIG
    bx = bounds or get_default_bounds()

    sx, sy = clamp_point(start, bx)
    tx, ty = clamp_point(target, bx)

    d = _dist((sx, sy), (tx, ty))
    if d <= cfg.close_px:
        return [PlannedStep(tx, ty, _rand(cfg.tick_min, cfg.tick_max))]

    d01 = _clamp(d / 650.0, 0.0, 1.0)
    curve_strength = cfg.curve_strength * (0.35 + 0.65 * d01)
    jitter_px = cfg.jitter_px * (0.20 + 0.80 * d01)

    speed = _rand(cfg.speed_min, cfg.speed_max)
    base_time = max(0.055, d / max(60.0, speed))

    # overshoot chance FIX (was ~65%)
    overshoot = 0.0
    if d > 70 and random.random() < 0.22:
        overshoot = _rand(cfg.overshoot_min, cfg.overshoot_max) * _clamp(d / 600.0, 0.6, 1.25)

    dx = tx - sx
    dy = ty - sy
    ang = math.atan2(dy, dx)

    ox = int(tx + math.cos(ang) * overshoot)
    oy = int(ty + math.sin(ang) * overshoot)
    ox, oy = clamp_point((ox, oy), bx)

    perp = ang + math.pi / 2.0
    curve_mag = curve_strength * _clamp(d, 70.0, 900.0) * _rand(-1.0, 1.0)

    cx = int(_lerp(sx, ox, 0.5) + math.cos(perp) * curve_mag)
    cy = int(_lerp(sy, oy, 0.5) + math.sin(perp) * curve_mag)
    cx, cy = clamp_point((cx, cy), bx)

    tick = _rand(cfg.tick_min, cfg.tick_max)
    n = int(_clamp(base_time / tick, 16, 340))

    dt_base = base_time / n
    dt_base = _clamp(dt_base, cfg.tick_min, cfg.tick_max)

    def bezier(t: float) -> Point:
        u = 1.0 - t
        x = u * u * sx + 2 * u * t * cx + t * t * ox
        y = u * u * sy + 2 * u * t * cy + t * t * oy
        return int(x), int(y)

    steps: List[PlannedStep] = []
    lastx, lasty = sx, sy

    for i in range(1, n + 1):
        t = i / n
        eased = _ease_in_out(t)

        if t > 0.75:
            tail = (t - 0.75) / 0.25
            eased -= (tail * tail) * cfg.end_slowdown * 0.10

        px, py = bezier(_clamp(eased, 0.0, 1.0))

        if i < n:
            px += int(_rand(-jitter_px, jitter_px))
            py += int(_rand(-jitter_px, jitter_px))

        px, py = clamp_point((px, py), bx)

        dt = dt_base
        if i < (n - 6) and random.random() < cfg.micro_pause_chance:
            dt += _rand(cfg.micro_pause_min, cfg.micro_pause_max)

        if px != lastx or py != lasty:
            steps.append(PlannedStep(px, py, dt))
            lastx, lasty = px, py

    # =========================
    # CORRECTION (FIX: no snapping)
    # =========================
    # remaining distance after ballistic
    rem = _dist((lastx, lasty), (tx, ty))

    # scale correction steps by remaining distance
    base_corr = int(_clamp(_lerp(cfg.correction_steps_min, cfg.correction_steps_max, d01),
                          cfg.correction_steps_min, cfg.correction_steps_max))

    # ensure enough steps so we don't "jump" at the end
    # max pixels per correction hop
    max_corr_step = 6.0
    extra = int(math.ceil(rem / max_corr_step)) if rem > 0 else 0
    corr_n = max(base_corr, extra, 3)

    corr_j = jitter_px * cfg.correction_jitter_scale

    cx2, cy2 = lastx, lasty
    for i in range(corr_n):
        # vector toward target, cap step length
        ddx = tx - cx2
        ddy = ty - cy2
        r = math.hypot(ddx, ddy)
        if r <= 1.0:
            break

        step_len = min(max_corr_step, r)
        k = step_len / max(1e-6, r)

        nx = int(round(cx2 + ddx * k))
        ny = int(round(cy2 + ddy * k))

        # tiny decaying jitter
        decay = 1.0 - (i / max(1.0, corr_n))
        nx += int(_rand(-corr_j * decay, corr_j * decay))
        ny += int(_rand(-corr_j * decay, corr_j * decay))

        nx, ny = clamp_point((nx, ny), bx)

        if (nx, ny) != (lastx, lasty):
            steps.append(PlannedStep(nx, ny, _clamp(dt_base * 0.95, cfg.tick_min, cfg.tick_max)))
            lastx, lasty = nx, ny
            cx2, cy2 = nx, ny
        else:
            # if rounding stalls, nudge 1px toward target
            nx = cx2 + (1 if ddx > 0 else -1 if ddx < 0 else 0)
            ny = cy2 + (1 if ddy > 0 else -1 if ddy < 0 else 0)
            nx, ny = clamp_point((nx, ny), bx)
            if (nx, ny) != (lastx, lasty):
                steps.append(PlannedStep(nx, ny, _clamp(dt_base, cfg.tick_min, cfg.tick_max)))
                lastx, lasty = nx, ny
                cx2, cy2 = nx, ny

    if (lastx, lasty) != (tx, ty):
        steps.append(PlannedStep(tx, ty, _rand(cfg.tick_min, cfg.tick_max)))

    return steps