from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Tuple

from .config import (
    PAUSE_DT_MS,
    STOP_SPEED_PX_S,
    TAIL_RADIUS_PX,
    P_TS, P_X, P_Y, P_DT_MS,
    P_SPEED, P_ACCEL, P_JERK, P_DHEADING, P_CURV,
)

Point = Tuple[Any, ...]


def now() -> float:
    return time.perf_counter()


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def median(vals: List[float]) -> float:
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return float(s[mid]) if n % 2 else float((s[mid - 1] + s[mid]) / 2)


def percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    if p <= 0:
        return float(s[0])
    if p >= 100:
        return float(s[-1])
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(s[int(k)])
    d0 = s[f] * (c - k)
    d1 = s[c] * (k - f)
    return float(d0 + d1)


def stat_pack(vals: List[float]) -> Dict[str, float]:
    return {
        "n": len(vals),
        "p10": round(percentile(vals, 10), 3) if vals else 0.0,
        "p50": round(percentile(vals, 50), 3) if vals else 0.0,
        "p90": round(percentile(vals, 90), 3) if vals else 0.0,
    }


def angle_wrap(a: float) -> float:
    while a <= -math.pi:
        a += 2 * math.pi
    while a > math.pi:
        a -= 2 * math.pi
    return a


def angle_diff(a: float, b: float) -> float:
    return angle_wrap(a - b)


def compute_trial(
    points: List[Point],
    target: Dict[str, Any],
    end_ts: float,
    outcome: str,
    mouse_xy_fallback: Tuple[int, int],
) -> Dict[str, Any]:
    pts = points[target["start_point_index"]:]
    if len(pts) < 3:
        pts = points[max(0, len(points) - 3):]

    center = target["center"]
    spawn_ts = target["spawn_ts"]
    end_ms = (end_ts - spawn_ts) * 1000.0

    speeds = [float(p[P_SPEED]) for p in pts]
    accs = [float(p[P_ACCEL]) for p in pts]
    jerks = [float(p[P_JERK]) for p in pts]
    dheads = [float(p[P_DHEADING]) for p in pts]

    # ✅ FIX: median speed should represent "movement", not settle/idle.
    # If you include lots of near-zero samples, median becomes 0.0 fast.
    MOVING_SPEED_THRESH = 25.0  # px/s; tweak 15..60 if needed
    speeds_moving = [s for s in speeds if s >= MOVING_SPEED_THRESH]

    max_speed = max(speeds) if speeds else 0.0
    if speeds_moving:
        med_speed = median(speeds_moving)
    else:
        # fallback: still give something instead of 0 unless truly empty
        med_speed = median(speeds) if speeds else 0.0

    stop_time_ms = 0.0
    pause_count = 0
    for p in pts:
        dt_ms = float(p[P_DT_MS])
        sp = float(p[P_SPEED])
        if sp < STOP_SPEED_PX_S and dt_ms > 0:
            stop_time_ms += dt_ms
        if dt_ms >= PAUSE_DT_MS:
            pause_count += 1

    enter_ts = target.get("first_enter_ts")
    if enter_ts is None and pts:
        for p in pts:
            x = int(p[P_X])
            y = int(p[P_Y])
            if (target["x1"] <= x <= target["x2"]) and (target["y1"] <= y <= target["y2"]):
                enter_ts = float(p[P_TS])
                break

    approach_ms = ((enter_ts - spawn_ts) * 1000.0) if enter_ts is not None else end_ms
    tail_ms = max(0.0, end_ms - approach_ms)

    dwell_in_target_ms = 0.0
    for p in pts:
        x = int(p[P_X]); y = int(p[P_Y])
        if (target["x1"] <= x <= target["x2"]) and (target["y1"] <= y <= target["y2"]):
            dwell_in_target_ms += max(0.0, float(p[P_DT_MS]))

    tail_pts: List[Point] = []
    for p in reversed(pts):
        xy = (float(p[P_X]), float(p[P_Y]))
        if dist(xy, center) <= TAIL_RADIUS_PX:
            tail_pts.append(p)
        else:
            if tail_pts:
                break
    tail_pts = list(reversed(tail_pts))

    overshoot_px = 0.0
    if tail_pts:
        dists = [dist((float(p[P_X]), float(p[P_Y])), center) for p in tail_pts]
        overshoot_px = max(0.0, max(dists) - min(dists)) if dists else 0.0

    if pts:
        end_x = float(pts[-1][P_X])
        end_y = float(pts[-1][P_Y])
    else:
        end_x, end_y = float(mouse_xy_fallback[0]), float(mouse_xy_fallback[1])

    dx_end = end_x - float(center[0])
    dy_end = end_y - float(center[1])
    radial_error = math.hypot(dx_end, dy_end)

    total_heading_change = sum(abs(x) for x in dheads) if dheads else 0.0
    curv_vals = [abs(float(p[P_CURV])) for p in pts]
    curv_p50 = percentile(curv_vals, 50) if curv_vals else 0.0
    curv_p90 = percentile(curv_vals, 90) if curv_vals else 0.0

    click_hold_ms = 0.0
    if target.get("click_down_ts") is not None and target.get("click_up_ts") is not None:
        click_hold_ms = max(0.0, (target["click_up_ts"] - target["click_down_ts"]) * 1000.0)

    pre_click_ms = 0.0
    if target.get("click_down_ts") is not None and enter_ts is not None:
        pre_click_ms = max(0.0, (target["click_down_ts"] - enter_ts) * 1000.0)

    return {
        "trial_id": target["trial_id"],
        "phase": int(target["phase"]),
        "label": target["label"],
        "outcome": outcome,
        "target_size": target["size"],
        "spawn_ts": round(spawn_ts, 6),
        "end_ts": round(end_ts, 6),

        "time_to_end_ms": round(end_ms, 3),
        "approach_time_ms": round(approach_ms, 3),
        "tail_time_ms": round(tail_ms, 3),
        "dwell_in_target_ms": round(dwell_in_target_ms, 3),

        "miss_clicks": int(target["miss_clicks"]),

        "center_x": round(center[0], 2),
        "center_y": round(center[1], 2),
        "end_x": round(end_x, 2),
        "end_y": round(end_y, 2),
        "end_dx": round(dx_end, 3),
        "end_dy": round(dy_end, 3),
        "end_radial_error": round(radial_error, 3),

        "overshoot_px": round(overshoot_px, 3),
        "max_speed_px_s": round(max_speed, 3),
        "median_speed_px_s": round(med_speed, 3),
        "stop_time_ms": round(stop_time_ms, 3),
        "pause_count": int(pause_count),

        "accel_p50": round(percentile(accs, 50), 3) if accs else 0.0,
        "jerk_p50": round(percentile(jerks, 50), 3) if jerks else 0.0,
        "jerk_p90": round(percentile(jerks, 90), 3) if jerks else 0.0,
        "heading_total_change": round(total_heading_change, 6),
        "curv_p50": round(curv_p50, 9),
        "curv_p90": round(curv_p90, 9),

        "pre_click_ms": round(pre_click_ms, 3),
        "click_hold_ms": round(click_hold_ms, 3),
        "points_in_trial": len(pts),
    }