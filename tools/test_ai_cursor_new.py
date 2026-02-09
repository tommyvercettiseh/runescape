from __future__ import annotations

import sys
import time
import json
import random
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_cursor_movement import plan_move, clamp_point, get_default_bounds, CursorMotionConfig
from config.areas import load_coords
from core.bot_offsets import apply_offset


def _today_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _compute_battery(used_sec: float, budget_sec: float) -> tuple[float | None, float | None]:
    budget_sec = float(budget_sec)
    used_sec = max(0.0, float(used_sec))
    if budget_sec <= 0:
        return None, None
    fatigue = used_sec / budget_sec
    if fatigue < 0.0:
        fatigue = 0.0
    if fatigue > 1.0:
        fatigue = 1.0
    battery = 1.0 - fatigue
    if battery < 0.0:
        battery = 0.0
    if battery > 1.0:
        battery = 1.0
    return fatigue, battery


def _load_manager_config() -> dict:
    path = ROOT / "botmanager_config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _pick_daily_budget_sec(cfg: dict, bot_id: int, *, date_str: str) -> float:
    """
    Mirror BotManager battery budget selection so dryruns match real runs:
      - If *_min/_max is set: deterministic uniform pick per bot per day.
      - Else: fixed hours/minutes (defaults to 8h).
    """

    def _get_float(key: str) -> float | None:
        v = cfg.get(key, None)
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            return None

    def _get_int(key: str, default: int) -> int:
        v = cfg.get(key, None)
        if v is None:
            return default
        try:
            return int(v)
        except Exception:
            return default

    # Range budgets (stable per bot per day)
    lo = _get_float(f"battery_budget_hours_min_{bot_id}")
    hi = _get_float(f"battery_budget_hours_max_{bot_id}")
    if lo is None or hi is None:
        lo = _get_float("battery_budget_hours_min")
        hi = _get_float("battery_budget_hours_max")

    if lo is not None and hi is not None:
        lo = max(0.0, float(lo))
        hi = max(0.0, float(hi))
        if hi < lo:
            lo, hi = hi, lo
        rng = random.Random(f"battery_budget_bot{int(bot_id)}_{date_str}")
        hours = rng.uniform(lo, hi)
        budget_sec = hours * 3600.0
        # Round to whole minutes so it stays human-readable.
        budget_sec = round(budget_sec / 60.0) * 60.0
        return float(max(0.0, budget_sec))

    # Fixed budgets
    gh = _get_int("battery_budget_hours", 8)
    gm = _get_int("battery_budget_minutes", 0)
    h = _get_int(f"battery_budget_hours_{bot_id}", gh)
    m = _get_int(f"battery_budget_minutes_{bot_id}", gm)

    if h < 0:
        h = 0
    if m < 0:
        m = 0
    if m > 59:
        m = 59
    return float(h * 3600 + m * 60)


def _rand_point_in_area(area_name: str, bot_id: int = 1, padding: int = 10) -> tuple[int, int]:
    x1, y1, x2, y2 = apply_offset(list(load_coords(area_name)), int(bot_id))
    left = int(x1 + padding)
    top = int(y1 + padding)
    right = int(x2 - padding - 1)
    bottom = int(y2 - padding - 1)
    if right <= left or bottom <= top:
        raise RuntimeError("Area te klein na padding")
    return random.randint(left, right), random.randint(top, bottom)


def _pick_points(area_name: str, bot_id: int, count: int = 7, padding: int = 10) -> list[tuple[int, int]]:
    pts = []
    for _ in range(count):
        pts.append(_rand_point_in_area(area_name, bot_id=bot_id, padding=padding))
    return pts


def _simulate_path_simple(start: tuple[int, int], target: tuple[int, int]) -> list[tuple[int, int, float]]:
    steps = plan_move(
        start,
        target,
        config=CursorMotionConfig(),
        bounds=get_default_bounds(),
        speed_pct=100.0,
    )
    out = []
    t = 0.0
    for st in steps:
        # ensure strictly increasing time
        t += max(float(st.sleep_s or 0.0), 0.0015)
        out.append((int(st.x), int(st.y), t))
    return out


def _bend_point(start: tuple[int, int], target: tuple[int, int], bounds, *, bias_x: float, min_px=8, max_px=42):
    x1, y1 = start
    x2, y2 = target
    dx = x2 - x1
    dy = y2 - y1
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 1.0:
        return target
    nx = -dy / dist
    ny = dx / dist
    offset = random.uniform(min_px, max_px)
    if random.random() < (0.55 + 0.2 * abs(bias_x)):
        sign = 1 if bias_x >= 0 else -1
    else:
        sign = 1 if random.random() < 0.5 else -1
    mid_t = random.uniform(0.35, 0.65)
    mx = x1 + dx * mid_t + nx * offset * sign
    my = y1 + dy * mid_t + ny * offset * sign
    return clamp_point((int(mx), int(my)), bounds)


def _simulate_path(start: tuple[int, int], target: tuple[int, int], *, bias_x: float) -> list[tuple[int, int, float]]:
    bounds = get_default_bounds()
    dist = ((target[0] - start[0]) ** 2 + (target[1] - start[1]) ** 2) ** 0.5
    if dist > 140 and random.random() < 0.28:
        mid = _bend_point(start, target, bounds, bias_x=bias_x)
        p1 = _simulate_path_simple(start, mid)
        p2 = _simulate_path_simple(mid, target)
        # rebase times for p2
        if p1:
            t0 = p1[-1][2]
        else:
            t0 = 0.0
        p2 = [(x, y, t + t0) for (x, y, t) in p2]
        return p1 + p2
    return _simulate_path_simple(start, target)


def _path_metrics(path: list[tuple[int, int, float]]) -> dict:
    if not path:
        return {"duration": 0.0, "length": 0.0, "max_speed": 0.0}
    length = 0.0
    max_speed = 0.0
    prev = None
    prev_t = 0.0
    for x, y, t in path:
        if prev is not None:
            dx = x - prev[0]
            dy = y - prev[1]
            dt = max(t - prev_t, 1e-6)
            dist = (dx * dx + dy * dy) ** 0.5
            length += dist
            max_speed = max(max_speed, dist / dt)
        prev = (x, y)
        prev_t = t
    return {"duration": float(path[-1][2]), "length": float(length), "max_speed": float(max_speed)}


def _micro_nudge(pos: tuple[int, int], bounds, *, min_px=1, max_px=3, bias_x: float = 0.0, bias_y: float = 0.0):
    dx = random.randint(min_px, max_px) * (1 if random.random() < 0.5 else -1)
    dy = random.randint(min_px, max_px) * (1 if random.random() < 0.5 else -1)
    dx += int(2 * bias_x)
    dy += int(2 * bias_y)
    return clamp_point((pos[0] + dx, pos[1] + dy), bounds)


def _pick_tail_mode(*, micro_pause_chance: float, pre_click_chance: float, tremor_chance: float, final_settle: bool) -> str:
    none_w = 0.60
    slow_w = float(micro_pause_chance) * 0.18 + (0.18 if final_settle else 0.0)
    drift_w = float(pre_click_chance) * 0.22
    wiggle_w = float(tremor_chance) * 0.18
    total = none_w + slow_w + drift_w + wiggle_w
    r = random.random() * total
    if r < none_w:
        return "none"
    r -= none_w
    if r < slow_w:
        return "slow"
    if r < slow_w + drift_w:
        return "drift"
    return "wiggle"


def _apply_tail_variation(path: list[tuple[int, int, float]], target: tuple[int, int], *, mode: str) -> list[tuple[int, int, float]]:
    if not path or mode == "none":
        if path:
            x, y, t = path[-1]
            path[-1] = (target[0], target[1], t)
        return path

    tail_len = min(len(path) - 1, random.randint(4, 10))
    if tail_len < 2:
        x, y, t = path[-1]
        path[-1] = (target[0], target[1], t)
        return path

    base_amp = random.uniform(1.0, 3.0)
    start_i = len(path) - tail_len

    # compute dt list so we can optionally slow the tail
    ts = [p[2] for p in path]
    dts = [ts[0]] + [ts[i] - ts[i - 1] for i in range(1, len(ts))]

    new_path = []
    acc_t = 0.0
    for i, (x, y, _) in enumerate(path):
        dt = dts[i]
        if start_i <= i < len(path) - 1:
            frac = (i - start_i) / max(1, tail_len - 1)
            decay = (1.0 - frac) ** 1.2
            amp = base_amp * decay

            if mode == "drift":
                dx = random.uniform(-amp, amp)
                dy = random.uniform(-amp, amp)
            elif mode == "wiggle":
                sign = -1 if (i % 2 == 0) else 1
                dx = sign * random.uniform(0.0, amp)
                dy = -sign * random.uniform(0.0, amp)
            else:
                dx = 0.0
                dy = 0.0

            x, y = clamp_point((int(round(x + dx)), int(round(y + dy))), get_default_bounds())

            if mode == "slow":
                dt *= random.uniform(1.05, 1.25)

        acc_t += max(dt, 0.0015)
        new_path.append((int(x), int(y), acc_t))

    # force exact end at target
    x, y, t = new_path[-1]
    new_path[-1] = (target[0], target[1], t)
    return new_path


def _compress_path(path: list[tuple[int, int, float]]) -> list[tuple[int, int, float]]:
    if not path:
        return path
    out: list[tuple[int, int, float]] = []
    last_x, last_y, acc_t = path[0]
    out.append((last_x, last_y, acc_t))
    for x, y, t in path[1:]:
        if (x, y) == (last_x, last_y):
            # accumulate time on last point
            out[-1] = (last_x, last_y, t)
        else:
            out.append((x, y, t))
            last_x, last_y = x, y
    return out


def _overshoot_point(start: tuple[int, int], target: tuple[int, int], bounds, *, bias_x: float) -> tuple[int, int]:
    x1, y1 = start
    x2, y2 = target
    dx = x2 - x1
    dy = y2 - y1
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 20:
        return target
    k = random.uniform(0.06, 0.18)
    ox = x2 + dx * k
    oy = y2 + dy * k
    nx = -dy / dist
    ny = dx / dist
    lat = random.uniform(2.0, 10.0)
    if random.random() < (0.55 + 0.2 * abs(bias_x)):
        sign = 1 if bias_x >= 0 else -1
    else:
        sign = 1 if random.random() < 0.5 else -1
    ox += nx * lat * sign
    oy += ny * lat * sign
    return clamp_point((int(round(ox)), int(round(oy))), bounds)


def _simulate_session(
    *,
    area: str,
    bot_id: int,
    hours: float,
    points: int,
    padding: int,
    battery_budget_sec: float,
) -> dict:
    sim_seconds = float(hours) * 3600.0
    pts = _pick_points(area, bot_id, count=points, padding=padding)

    bounds = get_default_bounds()
    cur = clamp_point(pts[0], bounds)
    t = 0.0
    events: list[dict] = []
    segments: list[dict] = []
    routes: list[dict] = []
    idx = 0
    seg_id = 0
    route_id = 0
    overshoot_count = 0
    idle_time = 0.0
    routine_id = f"dryrun_bot{bot_id}_{int(hours)}h_{int(time.time())}"
    date_str = _today_stamp()
    budget_sec = float(battery_budget_sec)

    # human rhythm waves: slow/fast phases
    phase_end = 0.0
    speed_wave = 1.0
    # fatigue model over long sessions
    fatigue = 0.0
    fatigue_rate = random.uniform(0.00002, 0.00006)  # per simulated second
    recovery_rate = fatigue_rate * 0.5
    # asymmetry bias per session (hand preference)
    bias_x = random.uniform(-0.22, 0.22)  # left/right bias
    bias_y = random.uniform(-0.18, 0.18)  # up/down bias

    while t < sim_seconds:
        route_id += 1
        route_start_t = t
        route_length = 0.0
        route_max_speed = 0.0
        route_overshoots = 0
        route_idle = 0.0

        target = pts[idx % len(pts)]

        # update rhythm phase
        if t >= phase_end:
            phase_end = t + random.uniform(12.0, 40.0)
            speed_wave = random.uniform(0.85, 1.18)

        # fatigue drift (build up over time, small recovery pockets)
        fatigue = min(1.0, fatigue + fatigue_rate * 12.0)
        if random.random() < 0.08:
            fatigue = max(0.0, fatigue - recovery_rate * random.uniform(5.0, 20.0))

        # occasional drift around target to avoid identical routes
        drift_dx = random.randint(-12, 12) + int(6 * bias_x)
        drift_dy = random.randint(-10, 10) + int(5 * bias_y)
        target = clamp_point((target[0] + drift_dx, target[1] + drift_dy), bounds)

        # occasional "dumb pause" before acting
        if random.random() < (0.04 + fatigue * 0.04):
            pause = random.uniform(0.20, 1.10 + fatigue * 1.4)
            t += pause
            idle_time += pause
            route_idle += pause

        # build one continuous movement path (single phase)
        dist = ((target[0] - cur[0]) ** 2 + (target[1] - cur[1]) ** 2) ** 0.5
        through_mode = "none"
        through = None
        if dist > 20 and random.random() < (0.22 + fatigue * 0.08 + (bias_x * 0.08)):
            through_mode = "overshoot"
            through = _overshoot_point(cur, target, bounds, bias_x=bias_x)
            overshoot_count += 1
            route_overshoots += 1
        elif dist > 20 and random.random() < (0.18 + fatigue * 0.10 - (bias_x * 0.05)):
            through_mode = "undershoot"
            ux = target[0] + random.randint(-10, 10)
            uy = target[1] + random.randint(-10, 10)
            through = clamp_point((ux, uy), bounds)
        elif dist > 140 and random.random() < 0.28:
            through_mode = "bend"
            through = _bend_point(cur, target, bounds, bias_x=bias_x)
        elif random.random() < (0.12 + fatigue * 0.10):
            through_mode = "detour"
            through = _rand_point_in_area(area, bot_id=bot_id, padding=padding)

        if through is not None:
            p1 = _simulate_path(cur, through, bias_x=bias_x)
            p2 = _simulate_path(through, target, bias_x=bias_x)
            t0 = p1[-1][2] if p1 else 0.0
            p2 = [(x, y, t + t0) for (x, y, t) in p2]
            path = p1 + p2
        else:
            path = _simulate_path(cur, target, bias_x=bias_x)

        tail_mode = _pick_tail_mode(
            micro_pause_chance=0.35 + fatigue * 0.12,
            pre_click_chance=0.42,
            tremor_chance=0.30 + fatigue * 0.10,
            final_settle=True,
        )
        path = _apply_tail_variation(path, target, mode=tail_mode)
        path = _compress_path(path)

        m = _path_metrics(path)
        seg_id += 1
        seg_start_t = t
        seg_from = {"x": cur[0], "y": cur[1]}
        seg_to = {"x": target[0], "y": target[1]}
        route_length += m["length"]
        route_max_speed = max(route_max_speed, m["max_speed"])
        for x, y, dt in path:
            t += dt * speed_wave * (1.0 + fatigue * 0.25)
            events.append({"t": round(t, 6), "x": x, "y": y, "segment_id": seg_id, "phase": "main", "routine_id": routine_id, "route_id": route_id})
        cur = clamp_point(target, bounds)
        seg_end_t = t
        bat_f0, bat_b0 = _compute_battery(seg_start_t, budget_sec)
        bat_f1, bat_b1 = _compute_battery(seg_end_t, budget_sec)
        segments.append(
            {
                "routine_id": routine_id,
                "route_id": route_id,
                "segment_id": seg_id,
                "phase": "main",
                "from": seg_from,
                "to": seg_to,
                "target_reached": True,
                "sim_t_start": round(seg_start_t, 6),
                "sim_t_end": round(seg_end_t, 6),
                "duration": round(m["duration"], 6),
                "path_length": round(m["length"], 3),
                "max_speed": round(m["max_speed"], 3),
                "through_mode": through_mode,
                "tail_mode": tail_mode,
                "battery_fatigue_start": bat_f0,
                "battery_fatigue_end": bat_f1,
                "battery_start": bat_b0,
                "battery_end": bat_b1,
            }
        )

        # idle dwell on target
        # occasional "cognitive pause"
        if random.random() < 0.06:
            pause = random.uniform(0.35, 1.65 + fatigue * 1.2)
            t += pause
            idle_time += pause
            route_idle += pause
        else:
            pause = random.uniform(0.05, 0.35 + fatigue * 0.20)
            t += pause
            idle_time += pause
            route_idle += pause

        # idle micro-noise (small wandering cluster, then return once)
        if random.random() < (0.30 + fatigue * 0.18):
            idle_steps = random.randint(2, 5)
            for _ in range(idle_steps):
                nx, ny = _micro_nudge(cur, bounds, min_px=1, max_px=3, bias_x=bias_x, bias_y=bias_y)
                jitter_path = _simulate_path(cur, (nx, ny), bias_x=bias_x)
                m = _path_metrics(jitter_path)
                seg_id += 1
                seg_start_t = t
                seg_from = {"x": cur[0], "y": cur[1]}
                seg_to = {"x": nx, "y": ny}
                route_length += m["length"]
                route_max_speed = max(route_max_speed, m["max_speed"])
                for x, y, dt in jitter_path:
                    t += dt * speed_wave
                    events.append({"t": round(t, 6), "x": x, "y": y, "segment_id": seg_id, "phase": "idle_jitter", "routine_id": routine_id, "route_id": route_id})
                cur = clamp_point((nx, ny), bounds)
                seg_end_t = t
                bat_f0, bat_b0 = _compute_battery(seg_start_t, budget_sec)
                bat_f1, bat_b1 = _compute_battery(seg_end_t, budget_sec)
                segments.append(
                    {
                        "routine_id": routine_id,
                        "route_id": route_id,
                        "segment_id": seg_id,
                        "phase": "idle_jitter",
                        "from": seg_from,
                        "to": seg_to,
                        "target_reached": False,
                        "sim_t_start": round(seg_start_t, 6),
                        "sim_t_end": round(seg_end_t, 6),
                        "duration": round(m["duration"], 6),
                        "path_length": round(m["length"], 3),
                        "max_speed": round(m["max_speed"], 3),
                        "battery_fatigue_start": bat_f0,
                        "battery_fatigue_end": bat_f1,
                        "battery_start": bat_b0,
                        "battery_end": bat_b1,
                    }
                )
            # single return to target at end of idle cluster
            jitter_back = _simulate_path(cur, target, bias_x=bias_x)
            m = _path_metrics(jitter_back)
            seg_id += 1
            seg_start_t = t
            seg_from = {"x": cur[0], "y": cur[1]}
            seg_to = {"x": target[0], "y": target[1]}
            route_length += m["length"]
            route_max_speed = max(route_max_speed, m["max_speed"])
            for x, y, dt in jitter_back:
                t += dt * speed_wave
                events.append({"t": round(t, 6), "x": x, "y": y, "segment_id": seg_id, "phase": "idle_return", "routine_id": routine_id, "route_id": route_id})
            cur = clamp_point(target, bounds)
            seg_end_t = t
            bat_f0, bat_b0 = _compute_battery(seg_start_t, budget_sec)
            bat_f1, bat_b1 = _compute_battery(seg_end_t, budget_sec)
            segments.append(
                {
                    "routine_id": routine_id,
                    "route_id": route_id,
                    "segment_id": seg_id,
                    "phase": "idle_return",
                    "from": seg_from,
                    "to": seg_to,
                    "target_reached": True,
                    "sim_t_start": round(seg_start_t, 6),
                    "sim_t_end": round(seg_end_t, 6),
                    "duration": round(m["duration"], 6),
                    "path_length": round(m["length"], 3),
                    "max_speed": round(m["max_speed"], 3),
                    "battery_fatigue_start": bat_f0,
                    "battery_fatigue_end": bat_f1,
                    "battery_start": bat_b0,
                    "battery_end": bat_b1,
                }
            )

        # route summary
        r_bat_f0, r_bat_b0 = _compute_battery(route_start_t, budget_sec)
        r_bat_f1, r_bat_b1 = _compute_battery(t, budget_sec)
        routes.append(
            {
                "route_id": route_id,
                "routine_id": routine_id,
                "target": {"x": target[0], "y": target[1]},
                "duration": round(t - route_start_t, 6),
                "path_length": round(route_length, 3),
                "max_speed": round(route_max_speed, 3),
                "overshoot_count": route_overshoots,
                "idle_time": round(route_idle, 6),
                "through_mode": through_mode,
                "tail_mode": tail_mode,
                "battery_fatigue_start": r_bat_f0,
                "battery_fatigue_end": r_bat_f1,
                "battery_start": r_bat_b0,
                "battery_end": r_bat_b1,
            }
        )

        idx += 1

    used_sec = float(t)
    bat_f, bat_b = _compute_battery(used_sec, budget_sec)
    return {
        "meta": {
            "routine_id": routine_id,
            "area": area,
            "bot_id": bot_id,
            "date": date_str,
            "hours": hours,
            "points": points,
            "events": len(events),
            "notes": "dryrun with single-phase moves, tail variation, fatigue, asymmetry, overshoot/undershoot",
            "battery": {
                "budget_sec": round(budget_sec, 6),
                "budget_hours": round(budget_sec / 3600.0, 6) if budget_sec > 0 else None,
                "used_sec": round(used_sec, 6),
                "fatigue": bat_f,
                "battery": bat_b,
                "source": "botmanager_config.json",
            },
        },
        "events": events,
        "segments": segments,
        "routes": routes,
        "stats": {
            "overshoot_count": overshoot_count,
            "idle_time": round(idle_time, 6),
            "segments": len(segments),
        },
    }


def main():
    area = "Bot_Area"
    bot_id = 1
    hours = 8.0
    points = 7
    padding = 8

    cfg = _load_manager_config()
    date_str = _today_stamp()
    budget_sec = _pick_daily_budget_sec(cfg, bot_id, date_str=date_str)

    print(f"[DryRun] ai_cursor simulate | area={area} bot={bot_id} hours={hours} points={points}")
    t0 = time.perf_counter()
    payload = _simulate_session(
        area=area,
        bot_id=bot_id,
        hours=hours,
        points=points,
        padding=padding,
        battery_budget_sec=budget_sec,
    )
    elapsed = time.perf_counter() - t0

    out_dir = ROOT / "recordings"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"dryrun_ai_cursor_bot{bot_id}_{int(hours)}h.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[DryRun] saved: {out_path}")
    print(f"[DryRun] elapsed: {elapsed:.3f}s")


if __name__ == "__main__":
    main()
