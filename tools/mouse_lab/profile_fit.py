from __future__ import annotations

from typing import Any, Dict, List

from .features import stat_pack


class ProfileBuilder:
    def build_profile_preview(self, trials: List[Dict[str, Any]], *, mode: str,
                              canvas_w: int, canvas_h: int, sampling_ms: int) -> Dict[str, Any]:
        profile: Dict[str, Any] = {
            "profile_id": "hes_signature_protocol_preview",
            "created_local": self._stamp(),
            "mode": mode,
            "resolution": [int(canvas_w), int(canvas_h)],
            "sampling_ms": int(sampling_ms),
            "globals": {},
            "by_phase": {},
        }

        if not trials:
            return profile

        g = trials
        profile["globals"] = {
            "time_to_end_ms": stat_pack([float(t["time_to_end_ms"]) for t in g]),
            "approach_time_ms": stat_pack([float(t["approach_time_ms"]) for t in g]),
            "tail_time_ms": stat_pack([float(t["tail_time_ms"]) for t in g]),
            "dwell_in_target_ms": stat_pack([float(t["dwell_in_target_ms"]) for t in g]),
            "overshoot_px": stat_pack([float(t["overshoot_px"]) for t in g]),
            "max_speed_px_s": stat_pack([float(t["max_speed_px_s"]) for t in g]),
            "median_speed_px_s": stat_pack([float(t["median_speed_px_s"]) for t in g]),
            "stop_time_ms": stat_pack([float(t["stop_time_ms"]) for t in g]),
            "miss_clicks": stat_pack([float(t["miss_clicks"]) for t in g]),
            "end_dx": stat_pack([float(t["end_dx"]) for t in g]),
            "end_dy": stat_pack([float(t["end_dy"]) for t in g]),
            "end_radial_error": stat_pack([float(t["end_radial_error"]) for t in g]),
            "jerk_p50": stat_pack([float(t["jerk_p50"]) for t in g]),
            "jerk_p90": stat_pack([float(t["jerk_p90"]) for t in g]),
            "curv_p90": stat_pack([float(t["curv_p90"]) for t in g]),
            "pre_click_ms": stat_pack([float(t["pre_click_ms"]) for t in g]),
            "click_hold_ms": stat_pack([float(t["click_hold_ms"]) for t in g]),
        }

        for ph in (1, 2, 3):
            items = [t for t in trials if int(t["phase"]) == ph]
            if not items:
                continue
            profile["by_phase"][str(ph)] = {
                "n": len(items),
                "time_to_end_ms": stat_pack([float(t["time_to_end_ms"]) for t in items]),
                "overshoot_px": stat_pack([float(t["overshoot_px"]) for t in items]),
                "max_speed_px_s": stat_pack([float(t["max_speed_px_s"]) for t in items]),
                "median_speed_px_s": stat_pack([float(t["median_speed_px_s"]) for t in items]),
                "end_radial_error": stat_pack([float(t["end_radial_error"]) for t in items]),
                "jerk_p90": stat_pack([float(t["jerk_p90"]) for t in items]),
            }

        return profile

    @staticmethod
    def _stamp() -> str:
        import time
        return time.strftime("%Y-%m-%d_%H%M%S")