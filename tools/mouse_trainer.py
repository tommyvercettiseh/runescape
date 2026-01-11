from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config"
CFG.mkdir(parents=True, exist_ok=True)

PROFILE_PATH = CFG / "mouse_profile.json"


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    k = (len(xs) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(xs[int(k)])
    return float(xs[f] + (xs[c] - xs[f]) * (k - f))


def _iqr(values: list[float]) -> float:
    return _pct(values, 0.75) - _pct(values, 0.25)


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


@dataclass
class Extracted:
    dt: list[float]
    move_len: list[float]
    move_speed: list[float]
    settle: list[float]
    hold: list[float]


def parse_log(path: Path) -> Extracted:
    data = json.loads(path.read_text(encoding="utf-8"))

    # Verwachting: events met type "move" en "click_down/click_up"
    # Pas mappings aan als jouw recorder andere keys gebruikt.
    events = data.get("events", data)

    dt: list[float] = []
    move_len: list[float] = []
    move_speed: list[float] = []
    settle: list[float] = []
    hold: list[float] = []

    last_move_t = None
    last_move_xy = None
    last_t = None

    down_t = None

    for e in events:
        t = float(e.get("t", e.get("time", 0.0)))
        et = e.get("type") or e.get("event")

        if last_t is not None and t > last_t:
            dt.append(t - last_t)
        last_t = t

        if et == "move":
            x = float(e.get("x"))
            y = float(e.get("y"))

            if last_move_t is not None and last_move_xy is not None:
                dx = x - last_move_xy[0]
                dy = y - last_move_xy[1]
                d = math.hypot(dx, dy)
                move_len.append(d)

                dtm = t - last_move_t
                if dtm > 0:
                    move_speed.append(d / dtm)

            last_move_t = t
            last_move_xy = (x, y)

        elif et in ("click_down", "mouse_down"):
            down_t = t
            if last_move_t is not None:
                settle.append(t - last_move_t)

        elif et in ("click_up", "mouse_up"):
            if down_t is not None:
                hold.append(t - down_t)
            down_t = None

    return Extracted(dt=dt, move_len=move_len, move_speed=move_speed, settle=settle, hold=hold)


def summarize(ex: Extracted) -> dict:
    def pack(xs: list[float]) -> dict:
        if not xs:
            return {"n": 0}
        return {
            "n": len(xs),
            "median": float(median(xs)),
            "p25": float(_pct(xs, 0.25)),
            "p75": float(_pct(xs, 0.75)),
            "iqr": float(_iqr(xs)),
            "p90": float(_pct(xs, 0.90)),
            "p95": float(_pct(xs, 0.95)),
        }

    return {
        "dt": pack(ex.dt),
        "move_len": pack(ex.move_len),
        "move_speed": pack(ex.move_speed),
        "settle": pack(ex.settle),
        "hold": pack(ex.hold),
    }


def merge_profile(old: dict, new: dict, alpha: float = 0.35) -> dict:
    # alpha = hoeveel gewicht nieuwe batch krijgt (0.0..1.0)
    def blend(a, b):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return (1 - alpha) * float(a) + alpha * float(b)
        return b

    out = dict(old)
    for k, v in new.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {kk: blend(out[k].get(kk), vv) for kk, vv in v.items()}
        else:
            out[k] = v
    return out


def build_cursor_params(profile: dict) -> dict:
    # Vertaal stats naar bruikbare defaults
    dt_med = profile.get("dt", {}).get("median", 0.008)
    fps = int(max(60, min(180, round(_safe_div(1.0, dt_med) if dt_med else 125))))

    settle_med = profile.get("settle", {}).get("median", 0.03)
    settle_p75 = profile.get("settle", {}).get("p75", 0.06)

    hold_med = profile.get("hold", {}).get("median", 0.08)
    hold_p75 = profile.get("hold", {}).get("p75", 0.14)

    return {
        "fps": fps,
        "settle_min_s": float(max(0.005, settle_med * 0.35)),
        "settle_max_s": float(max(0.02, settle_p75 * 1.05)),
        "press_min_s": float(max(0.03, hold_med * 0.60)),
        "press_max_s": float(max(0.06, hold_p75 * 1.05)),
    }


def main():
    rec_dir = ROOT / "recordings"
    rec_dir.mkdir(parents=True, exist_ok=True)

    logs = sorted(rec_dir.glob("*.json"))
    if not logs:
        print("⚠️ Geen recordings gevonden in /recordings")
        return

    batch_stats = []
    for p in logs:
        ex = parse_log(p)
        batch_stats.append(summarize(ex))

    # Combine batch: neem medianen van medianen (simpel, werkt prima)
    def med_of(key: str, field: str) -> float:
        vals = [b.get(key, {}).get(field) for b in batch_stats]
        vals = [v for v in vals if isinstance(v, (int, float))]
        return float(median(vals)) if vals else 0.0

    combined = {
        "dt": {"median": med_of("dt", "median"), "p75": med_of("dt", "p75"), "p95": med_of("dt", "p95")},
        "settle": {"median": med_of("settle", "median"), "p75": med_of("settle", "p75")},
        "hold": {"median": med_of("hold", "median"), "p75": med_of("hold", "p75")},
        "move_speed": {"median": med_of("move_speed", "median"), "p75": med_of("move_speed", "p75")},
    }

    old = {}
    if PROFILE_PATH.exists():
        old = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

    merged = merge_profile(old, combined, alpha=0.35)
    merged["derived"] = build_cursor_params(merged)

    PROFILE_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✅ Profile updated → {PROFILE_PATH}")


if __name__ == "__main__":
    main()
