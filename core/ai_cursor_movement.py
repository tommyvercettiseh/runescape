# core/ai_cursor_movement.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence, Tuple
import math
import random

Point = Tuple[int, int]
Bounds = Tuple[int, int, int, int]  # x1,y1,x2,y2


# ============================================================
# Config
# ============================================================

@dataclass(frozen=True)
class CursorMotionConfig:
    # timing
    duration: float = 0.22          # seconds
    fps: int = 120

    # step safety
    min_steps: int = 12
    min_duration: float = 0.06

    # motor feel
    overshoot_chance: float = 0.22
    overshoot_px_mean: float = 9.0
    overshoot_px_sd: float = 5.0

    micro_jitter_px: float = 0.55   # 0..2-ish
    endpoint_settle_ms: int = 28    # small finishing settle

    # noise shaping
    tremor_strength: float = 0.10   # 0..0.3
    fatigue_strength: float = 0.0   # 0..1 external, shifts speed + jitter


# ============================================================
# Helpers
# ============================================================

def clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


def clamp_point(p: Point, b: Bounds) -> Point:
    x1, y1, x2, y2 = b
    return (int(clamp(p[0], x1, x2)), int(clamp(p[1], y1, y2)))


def dist(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    # nice accel and decel, 0..1
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ease_in_out_sine(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * t)


def _randn(mean: float, sd: float) -> float:
    # gaussian
    return random.gauss(mean, sd)


def _unit_vec(a: Point, b: Point) -> Tuple[float, float]:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    d = math.hypot(dx, dy) or 1.0
    return (dx / d, dy / d)


def _perp(u: Tuple[float, float]) -> Tuple[float, float]:
    return (-u[1], u[0])


def _bezier(p0, p1, p2, p3, t: float) -> Tuple[float, float]:
    # cubic bezier
    u = 1.0 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t
    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return (x, y)


# ============================================================
# Planning
# ============================================================

def plan_move(
    start: Point,
    target: Point,
    motion: CursorMotionConfig,
    *,
    bounds: Optional[Bounds] = None,
    rng: Optional[random.Random] = None,
) -> List[Point]:
    """
    Returns list of integer points along a human-ish trajectory.
    This module does NOT move the cursor. Only plans a path.
    """
    r = rng or random
    p0 = (float(start[0]), float(start[1]))
    p3 = (float(target[0]), float(target[1]))

    duration = max(float(motion.min_duration), float(motion.duration))
    fps = max(30, int(motion.fps))
    steps = max(int(motion.min_steps), int(duration * fps))

    # fatigue shifts: more jitter + slightly slower profile
    fatigue = clamp(float(motion.fatigue_strength), 0.0, 1.0)
    jitter = float(motion.micro_jitter_px) * (1.0 + 0.85 * fatigue)

    # direction + distance
    d = dist(start, target)
    u = _unit_vec(start, target)
    v = _perp(u)

    # control points
    # lateral deviation grows with distance but saturates
    lateral = clamp(_randn(0.0, 1.0), -2.0, 2.0) * clamp(d / 120.0, 0.25, 1.8) * 10.0
    along1 = clamp(d * r.uniform(0.20, 0.38), 10.0, 420.0)
    along2 = clamp(d * r.uniform(0.58, 0.80), 20.0, 520.0)

    p1 = (p0[0] + u[0] * along1 + v[0] * lateral,
          p0[1] + u[1] * along1 + v[1] * lateral)

    p2 = (p0[0] + u[0] * along2 + v[0] * (-lateral * r.uniform(0.65, 1.25)),
          p0[1] + u[1] * along2 + v[1] * (-lateral * r.uniform(0.65, 1.25)))

    # optional overshoot: create a slightly past target endpoint, then correction later
    do_overshoot = (r.random() < float(motion.overshoot_chance)) and d > 35
    if do_overshoot:
        ov = max(0.0, _randn(float(motion.overshoot_px_mean), float(motion.overshoot_px_sd)))
        ov = clamp(ov, 2.0, 45.0)
        p3_os = (p3[0] + u[0] * ov, p3[1] + u[1] * ov)
        main_path = _sample_bezier(p0, p1, p2, p3_os, steps, jitter=jitter, tremor=float(motion.tremor_strength))
        # correction mini-path
        corr_steps = max(8, int(steps * r.uniform(0.10, 0.22)))
        corr = _sample_bezier(
            (float(main_path[-1][0]), float(main_path[-1][1])),
            (p3_os[0] + v[0] * r.uniform(-3, 3), p3_os[1] + v[1] * r.uniform(-3, 3)),
            (p3[0] + v[0] * r.uniform(-2, 2), p3[1] + v[1] * r.uniform(-2, 2)),
            p3,
            corr_steps,
            jitter=jitter * 0.55,
            tremor=float(motion.tremor_strength) * 0.6,
        )
        pts = main_path + corr
    else:
        pts = _sample_bezier(p0, p1, p2, p3, steps, jitter=jitter, tremor=float(motion.tremor_strength))

    # clamp + de-dupe
    out: List[Point] = []
    last = None
    for x, y in pts:
        pi = (int(round(x)), int(round(y)))
        if bounds is not None:
            pi = clamp_point(pi, bounds)
        if last != pi:
            out.append(pi)
            last = pi

    # ensure ends at exact target
    if out and out[-1] != (int(target[0]), int(target[1])):
        out.append((int(target[0]), int(target[1])))

    return out


def _sample_bezier(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    steps: int,
    *,
    jitter: float,
    tremor: float,
) -> List[Tuple[float, float]]:
    pts: List[Tuple[float, float]] = []
    steps = max(2, int(steps))

    for i in range(steps):
        t = i / (steps - 1)

        # human-ish speed curve: sine ease with tiny irregularity
        base = ease_in_out_sine(t)
        wobble = (random.random() - 0.5) * 0.018
        t2 = clamp(base + wobble, 0.0, 1.0)

        x, y = _bezier(p0, p1, p2, p3, t2)

        # micro jitter fades towards endpoint
        fade = 1.0 - smoothstep(t)
        j = jitter * fade
        x += (random.random() - 0.5) * 2.0 * j
        y += (random.random() - 0.5) * 2.0 * j

        # tremor is tiny oscillation, not full randomness
        if tremor > 0.0:
            trem = tremor * fade
            x += math.sin(t * math.pi * 6.0) * trem * 2.0
            y += math.cos(t * math.pi * 5.0) * trem * 2.0

        pts.append((x, y))

    return pts