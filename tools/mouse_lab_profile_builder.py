# profile_builder.py
# Build 1 master profile from all mouse_profile/*/*/trials.csv
# Output: mouse_profile/master_profile.json + master_profile_summary.txt

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

BASE_DIR = Path("mouse_profile")

# Welke trial-metrics je wil aggregeren (best “engine-relevant”)
METRICS = [
    "time_to_end_ms",
    "approach_time_ms",
    "tail_time_ms",
    "dwell_in_target_ms",
    "overshoot_px",
    "max_speed_px_s",
    "median_speed_px_s",
    "stop_time_ms",
    "pause_count",
    "miss_clicks",
    "end_dx",
    "end_dy",
    "end_radial_error",
    "accel_p50",
    "jerk_p50",
    "jerk_p90",
    "heading_total_change",
    "curv_p50",
    "curv_p90",
    "pre_click_ms",
    "click_hold_ms",
]

PHASES = (1, 2, 3)


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
    if not vals:
        return {"n": 0, "mean": 0.0, "std": 0.0, "p10": 0.0, "p50": 0.0, "p90": 0.0}
    n = len(vals)
    mean = sum(vals) / n
    var = sum((x - mean) ** 2 for x in vals) / max(1, (n - 1))
    std = math.sqrt(var)
    return {
        "n": n,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "p10": round(percentile(vals, 10), 4),
        "p50": round(percentile(vals, 50), 4),
        "p90": round(percentile(vals, 90), 4),
    }


def try_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except Exception:
        return None


def find_trial_files(base_dir: Path) -> List[Path]:
    # matches mouse_profile/YYYY-MM-DD/SESSION/trials.csv
    return sorted(base_dir.glob("*/*/trials.csv"))


def load_trials(trials_csv: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(trials_csv, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def build_master_profile(base_dir: Path) -> Tuple[Dict[str, Any], str]:
    trial_files = find_trial_files(base_dir)

    all_trials: List[Dict[str, Any]] = []
    used_runs: List[str] = []

    for tf in trial_files:
        run_dir = tf.parent
        run_id = f"{run_dir.parent.name}/{run_dir.name}"  # YYYY-MM-DD/SESSION
        try:
            trials = load_trials(tf)
        except Exception:
            continue

        if not trials:
            continue

        # Keep run metadata if present
        for t in trials:
            t["_run_id"] = run_id

        all_trials.extend(trials)
        used_runs.append(run_id)

    # Filter: only HIT trials (your lab marks outcome="HIT")
    hit_trials = [t for t in all_trials if str(t.get("outcome", "")).upper() == "HIT"]

    # Prepare buckets
    buckets_global: Dict[str, List[float]] = {m: [] for m in METRICS}
    buckets_phase: Dict[int, Dict[str, List[float]]] = {ph: {m: [] for m in METRICS} for ph in PHASES}

    # Fill buckets
    for t in hit_trials:
        ph = int(float(t.get("phase", 0) or 0))
        for m in METRICS:
            v = try_float(t.get(m))
            if v is None:
                continue
            buckets_global[m].append(v)
            if ph in buckets_phase:
                buckets_phase[ph][m].append(v)

    # Build profile json
    profile: Dict[str, Any] = {
        "profile_id": "hes_master_profile_v1",
        "source_dir": str(base_dir),
        "runs_found": len(trial_files),
        "runs_used": len(set(used_runs)),
        "trials_total": len(all_trials),
        "trials_hit": len(hit_trials),
        "globals": {},
        "by_phase": {},
        "notes": {
            "aggregation": "All runs merged. outcome=HIT only. stats include mean/std/p10/p50/p90.",
            "metrics": METRICS,
        },
    }

    for m in METRICS:
        profile["globals"][m] = stat_pack(buckets_global[m])

    for ph in PHASES:
        blk: Dict[str, Any] = {"n_trials": len([t for t in hit_trials if int(float(t.get('phase',0) or 0)) == ph])}
        for m in METRICS:
            blk[m] = stat_pack(buckets_phase[ph][m])
        profile["by_phase"][str(ph)] = blk

    # Human readable summary
    lines: List[str] = []
    lines.append("Mouse Profile · Master Summary")
    lines.append(f"base_dir: {base_dir}")
    lines.append(f"runs_found (with trials.csv): {profile['runs_found']}")
    lines.append(f"runs_used: {profile['runs_used']}")
    lines.append(f"trials_total: {profile['trials_total']}")
    lines.append(f"trials_hit: {profile['trials_hit']}")
    lines.append("")
    lines.append("Globals (mean/std/p10/p50/p90):")
    for m in METRICS:
        s = profile["globals"][m]
        lines.append(f"  {m}: n={s['n']} mean={s['mean']} std={s['std']} p10={s['p10']} p50={s['p50']} p90={s['p90']}")
    lines.append("")
    lines.append("By phase:")
    for ph in PHASES:
        blk = profile["by_phase"][str(ph)]
        lines.append(f"  phase {ph}: n_trials={blk['n_trials']}")
        for m in METRICS:
            s = blk[m]
            lines.append(f"    {m}: n={s['n']} mean={s['mean']} std={s['std']} p10={s['p10']} p50={s['p50']} p90={s['p90']}")

    return profile, "\n".join(lines)


def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    profile, summary = build_master_profile(BASE_DIR)

    out_json = BASE_DIR / "master_profile.json"
    out_txt = BASE_DIR / "master_profile_summary.txt"

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"✅ Saved: {out_json}")
    print(f"✅ Saved: {out_txt}")


if __name__ == "__main__":
    main()