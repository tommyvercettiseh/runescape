from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _weighted_median(pairs: List[Tuple[float, float]]) -> float:
    """
    pairs: [(value, weight), ...]
    returns weighted median. If weights are all 0, falls back to simple median.
    """
    if not pairs:
        return 0.0

    cleaned = [(float(v), max(0.0, float(w))) for v, w in pairs]
    total_w = sum(w for _, w in cleaned)
    cleaned.sort(key=lambda t: t[0])

    if total_w <= 0:
        vals = [v for v, _ in cleaned]
        vals.sort()
        n = len(vals)
        mid = n // 2
        return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0

    acc = 0.0
    half = total_w / 2.0
    for v, w in cleaned:
        acc += w
        if acc >= half:
            return v
    return cleaned[-1][0]


def _aggregate_stat(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    entries: list of dicts like {"n":..,"p10":..,"p50":..,"p90":..}
    We do weighted medians using "n" as weight.
    """
    pairs_p10: List[Tuple[float, float]] = []
    pairs_p50: List[Tuple[float, float]] = []
    pairs_p90: List[Tuple[float, float]] = []
    n_sum = 0.0

    for e in entries:
        if not isinstance(e, dict):
            continue
        w = _safe_float(e.get("n", 0), 0.0)
        n_sum += w
        pairs_p10.append((_safe_float(e.get("p10", 0.0), 0.0), w))
        pairs_p50.append((_safe_float(e.get("p50", 0.0), 0.0), w))
        pairs_p90.append((_safe_float(e.get("p90", 0.0), 0.0), w))

    return {
        "n": int(round(n_sum)),
        "p10": round(_weighted_median(pairs_p10), 3),
        "p50": round(_weighted_median(pairs_p50), 3),
        "p90": round(_weighted_median(pairs_p90), 3),
    }


def _list_previews(recordings_dir: Path) -> List[Path]:
    previews = list(recordings_dir.rglob("profile_preview.json"))
    previews = [p for p in previews if p.is_file()]
    previews.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return previews


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _derive_ai_cursor_mapping(globals_stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience mapping into the keys your ai_cursor already uses.
    Uses p50/p90 from master globals.
    """
    def g(metric: str, key: str, default: float) -> float:
        blk = globals_stats.get(metric) or {}
        if not isinstance(blk, dict):
            return default
        return _safe_float(blk.get(key, default), default)

    # Use median speed (moving) as baseline, max speed as ceiling hint
    med_p50 = g("median_speed_px_s", "p50", 900.0)
    med_p90 = g("median_speed_px_s", "p90", 1500.0)

    over_p50 = g("overshoot_px", "p50", 8.0)
    over_p90 = g("overshoot_px", "p90", 20.0)

    pre_click_s = g("pre_click_ms", "p50", 90.0) / 1000.0
    click_hold_s = g("click_hold_ms", "p50", 35.0) / 1000.0

    tail_s = g("tail_time_ms", "p50", 90.0) / 1000.0
    stop_s = g("stop_time_ms", "p50", 45.0) / 1000.0
    settle_s = max(0.02, min(0.25, (tail_s * 0.65) + (stop_s * 0.35)))

    speed_min = max(200.0, med_p50 * 0.78)
    speed_max = max(speed_min + 80.0, med_p90 * 1.05)

    overshoot_min = max(1.0, over_p50 * 0.70)
    overshoot_max = max(overshoot_min + 1.0, over_p90 * 1.15)

    return {
        "mouse_profile": {
            "speed_min": round(speed_min, 3),
            "speed_max": round(speed_max, 3),
            "overshoot_min": round(overshoot_min, 3),
            "overshoot_max": round(overshoot_max, 3),
            "pre_click_s": round(max(0.0, min(0.45, pre_click_s)), 6),
            "click_hold_s": round(max(0.006, min(0.30, click_hold_s)), 6),
            "settle_s": round(settle_s, 6),
            "close_px": 2.2,
        }
    }


def build_master(preview_paths: List[Path]) -> Dict[str, Any]:
    sources: List[str] = []
    globals_by_metric: Dict[str, List[Dict[str, Any]]] = {}
    by_phase_by_metric: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    mode = None
    sampling_ms = None
    resolution = None

    for p in preview_paths:
        try:
            data = _load_json(p)
            if not isinstance(data, dict):
                continue

            g = data.get("globals") or {}
            bp = data.get("by_phase") or {}

            if mode is None:
                mode = data.get("mode")
            if sampling_ms is None:
                sampling_ms = data.get("sampling_ms")
            if resolution is None:
                resolution = data.get("resolution")

            if isinstance(g, dict):
                for metric, stats in g.items():
                    if isinstance(stats, dict):
                        globals_by_metric.setdefault(metric, []).append(stats)

            if isinstance(bp, dict):
                for phase_key, blk in bp.items():
                    if not isinstance(blk, dict):
                        continue
                    for metric, stats in blk.items():
                        if metric == "n":
                            continue
                        if isinstance(stats, dict):
                            by_phase_by_metric.setdefault(phase_key, {}).setdefault(metric, []).append(stats)

            sources.append(str(p))
        except Exception:
            continue

    master_globals: Dict[str, Any] = {}
    for metric, entries in globals_by_metric.items():
        master_globals[metric] = _aggregate_stat(entries)

    master_by_phase: Dict[str, Any] = {}
    for phase_key, metrics in by_phase_by_metric.items():
        out_blk: Dict[str, Any] = {}
        n_guess = 0
        for metric, entries in metrics.items():
            agg = _aggregate_stat(entries)
            out_blk[metric] = agg
            n_guess = max(n_guess, int(agg.get("n", 0)))
        out_blk["n"] = n_guess
        master_by_phase[phase_key] = out_blk

    out = {
        "profile_id": "hes_master_profile",
        "kind": "master_profile",
        "created_local": __import__("time").strftime("%Y-%m-%d_%H%M%S"),
        "mode": mode or "MIXED",
        "resolution": resolution or [0, 0],
        "sampling_ms": int(sampling_ms) if sampling_ms is not None else None,
        "sources": sources,
        "globals": master_globals,
        "by_phase": master_by_phase,
    }

    out["ai_cursor_mapping"] = _derive_ai_cursor_mapping(master_globals)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5, help="How many latest runs to combine")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent  # .../tools/mouse_lab
    recordings_dir = here / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)

    previews = _list_previews(recordings_dir)
    if not previews:
        raise SystemExit(f"Geen profile_preview.json gevonden in: {recordings_dir}")

    chosen = previews[: max(1, args.n)]
    master = build_master(chosen)

    out_path = recordings_dir / "master_profile.json"
    out_path.write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")

    print("✅ master_profile geschreven:", out_path)
    print("✅ runs gebruikt:", len(master.get("sources", [])))
    print("✅ ai_cursor_mapping:", master["ai_cursor_mapping"]["mouse_profile"])


if __name__ == "__main__":
    main()