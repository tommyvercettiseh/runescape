from __future__ import annotations

import csv
import json
import platform
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


def datetime_stamp_local() -> str:
    return time.strftime("%Y-%m-%d_%H%M%S")


def unique_run_dir(base_dir: Path) -> Path:
    day_dir = base_dir / time.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    base_name = datetime_stamp_local()
    run_dir = day_dir / base_name
    if not run_dir.exists():
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    i = 2
    while True:
        alt = day_dir / f"{base_name}_{i}"
        if not alt.exists():
            alt.mkdir(parents=True, exist_ok=False)
            return alt
        i += 1


class Exporter:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.run_dir = unique_run_dir(self.base_dir)
        self.session_id = self.run_dir.name

        self.points_csv = self.run_dir / "mouse_points.csv"
        self.events_csv = self.run_dir / "events.csv"
        self.trials_csv = self.run_dir / "trials.csv"
        self.summary_txt = self.run_dir / "summary.txt"
        self.meta_json = self.run_dir / "meta.json"
        self.profile_json = self.run_dir / "profile_preview.json"

    def write_meta(self, *, mode: str, sample_ms: int,
                   root_screen_w: int, root_screen_h: int,
                   window_w: int, window_h: int, dpi: float,
                   protocol: Dict[str, Any]) -> None:
        polling_hz = int(round(1000.0 / float(sample_ms)))
        meta = {
            "session_id": self.session_id,
            "created_local": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": mode,
            "sampling_ms": int(sample_ms),
            "polling_hz": polling_hz,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "screen_w": int(root_screen_w),
            "screen_h": int(root_screen_h),
            "window_w": int(window_w),
            "window_h": int(window_h),
            "dpi": float(dpi),
            "protocol": protocol,
        }
        with open(self.meta_json, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    def write_points(self, points: List[Tuple[Any, ...]]) -> None:
        with open(self.points_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "ts", "x", "y", "buttons", "active_trial_id", "dt_ms",
                "vx", "vy", "speed_px_s", "ax", "ay", "accel_px_s2", "jerk_px_s3",
                "heading_rad", "dheading_rad", "curv", "dist_to_target", "inside_target",
                "target_trial_id", "label", "target_cx", "target_cy", "target_size"
            ])
            w.writerows(points)

    def write_dict_rows(self, path: Path, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        cols = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)

    def write_profile_json(self, profile: Dict[str, Any]) -> None:
        with open(self.profile_json, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

    def write_summary(self, profile: Dict[str, Any], *, mode: str,
                      phase1_reps: int, phase2_reps: int, phase3_blocks: int) -> None:
        lines = []
        lines.append("Mouse Lab · Hes Signature Protocol Summary")
        lines.append(f"session_id: {self.session_id}")
        lines.append(f"mode: {mode}")
        lines.append(f"phase1_reps: {phase1_reps}")
        lines.append(f"phase2_reps: {phase2_reps}")
        lines.append(f"phase3_blocks: {phase3_blocks}")
        lines.append("")
        lines.append("Globals (p10/p50/p90):")
        for k, v in profile.get("globals", {}).items():
            lines.append(f"  {k}: n={v.get('n')} p10={v.get('p10')} p50={v.get('p50')} p90={v.get('p90')}")
        lines.append("")
        lines.append("By phase:")
        for ph, blk in profile.get("by_phase", {}).items():
            lines.append(f"  phase {ph} (n={blk.get('n')}):")
            for k, v in blk.items():
                if k == "n":
                    continue
                lines.append(f"    {k}: n={v.get('n')} p10={v.get('p10')} p50={v.get('p50')} p90={v.get('p90')}")

        with open(self.summary_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))