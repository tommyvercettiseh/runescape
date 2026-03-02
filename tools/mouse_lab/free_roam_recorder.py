from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import SAMPLE_MS, BASE_DIR
from .features import now, angle_diff
from .export import Exporter


try:
    from pynput import mouse, keyboard
except Exception as e:
    raise SystemExit("❌ pynput ontbreekt. pip install pynput") from e


Point = Tuple[Any, ...]


class FreeRoamRecorder:
    """
    Fully compatible with Exporter:
    - mouse_points.csv (exact 23 cols)
    - events.csv via write_dict_rows
    - trials.csv used as segments
    - meta.json correct structure
    """

    def __init__(
        self,
        *,
        sample_ms_active: int = SAMPLE_MS,
        sample_ms_idle: int = 150,
        idle_after_s: float = 8.0,
        cut_after_idle_s: float = 90.0,
        stop_after_idle_s: Optional[float] = None,
    ):
        self.sample_ms_active = int(sample_ms_active)
        self.sample_ms_idle = int(sample_ms_idle)
        self.idle_after_s = float(idle_after_s)
        self.cut_after_idle_s = float(cut_after_idle_s)
        self.stop_after_idle_s = float(stop_after_idle_s) if stop_after_idle_s else None

        self.exporter = Exporter(BASE_DIR / "free_roam")
        self.session_id = self.exporter.session_id

        # runtime state
        self.running = False
        self.mouse_x = 0
        self.mouse_y = 0
        self.buttons = 0

        self.points: List[Point] = []
        self.events: List[Dict[str, Any]] = []
        self.segments: List[Dict[str, Any]] = []

        self.last_sample_ts: Optional[float] = None
        self.last_sample_xy: Optional[Tuple[int, int]] = None

        self._last_vx = self._last_vy = 0.0
        self._last_ax = self._last_ay = 0.0
        self._last_heading = 0.0

        self._last_active_ts = now()
        self._idle = False
        self._seg_id = 1
        self._seg_start = now()

        self._mouse_ctrl = mouse.Controller()

    # ----------------------------
    # EVENT LOGGING (schema exact match)
    # ----------------------------
    def log_event(self, event_type: str, extra: Optional[Dict[str, Any]] = None):
        row = {
            "session_id": self.session_id,
            "t": round(now(), 6),
            "x": int(self.mouse_x),
            "y": int(self.mouse_y),
            "event_type": event_type,
            "buttons": int(self.buttons),
            "button": "",
            "click_id": "",
            "target_id": "",
            "label": f"FREE_ROAM|seg={self._seg_id}",
            "phase": "",
            "extra": extra or {},
        }
        self.events.append(row)

    # ----------------------------
    # IDLE / SEGMENT LOGIC
    # ----------------------------
    def _mark_active(self):
        self._last_active_ts = now()
        if self._idle:
            self._idle = False
            self.log_event("idle_end")

    def _handle_idle(self):
        idle_for = now() - self._last_active_ts

        if (not self._idle) and idle_for >= self.idle_after_s:
            self._idle = True
            self.log_event("idle_start")

        if idle_for >= self.cut_after_idle_s:
            self._cut_segment(idle_for)

        if self.stop_after_idle_s and idle_for >= self.stop_after_idle_s:
            self.log_event("auto_stop")
            self.stop()

    def _cut_segment(self, idle_for):
        self.segments.append({
            "segment_id": self._seg_id,
            "start_t": round(self._seg_start, 6),
            "end_t": round(now(), 6),
            "idle_seconds": round(idle_for, 3),
        })
        self._seg_id += 1
        self._seg_start = now()
        self._idle = False
        self._last_active_ts = now()
        self.last_sample_ts = None
        self.last_sample_xy = None
        self.log_event("segment_start")

    # ----------------------------
    # SAMPLING (MATCHES HEADER EXACTLY)
    # ----------------------------
    def _sample_once(self):
        ts = now()

        x, y = self._mouse_ctrl.position
        self.mouse_x, self.mouse_y = int(x), int(y)

        if self.last_sample_ts is None:
            dt = 0.0
            dt_ms = 0.0
        else:
            dt = ts - self.last_sample_ts
            dt_ms = dt * 1000.0

        if self.last_sample_xy is None or dt <= 0:
            vx = vy = ax = ay = jerk = 0.0
            heading = self._last_heading
            dheading = curv = 0.0
        else:
            dx = self.mouse_x - self.last_sample_xy[0]
            dy = self.mouse_y - self.last_sample_xy[1]

            vx = dx / dt
            vy = dy / dt
            ax = (vx - self._last_vx) / dt
            ay = (vy - self._last_vy) / dt

            jx = (ax - self._last_ax) / dt
            jy = (ay - self._last_ay) / dt
            jerk = math.hypot(jx, jy)

            speed_step = math.hypot(vx, vy)
            if speed_step > 1e-9:
                heading = math.atan2(vy, vx)
                dheading = angle_diff(heading, self._last_heading)
                ds = math.hypot(dx, dy)
                curv = abs(dheading) / max(1e-6, ds)
            else:
                heading = self._last_heading
                dheading = curv = 0.0

        speed = math.hypot(vx, vy)
        accel = math.hypot(ax, ay)

        self.last_sample_ts = ts
        self.last_sample_xy = (self.mouse_x, self.mouse_y)
        self._last_vx, self._last_vy = vx, vy
        self._last_ax, self._last_ay = ax, ay
        self._last_heading = heading

        self.points.append((
            ts, self.mouse_x, self.mouse_y, self.buttons, "",
            dt_ms, vx, vy, speed,
            ax, ay, accel, jerk,
            heading, dheading, curv,
            0.0, 0,
            "", f"FREE_ROAM|seg={self._seg_id}",
            0.0, 0.0, ""
        ))

        self._handle_idle()

        sleep_ms = self.sample_ms_idle if self._idle else self.sample_ms_active
        time.sleep(max(0.001, sleep_ms / 1000.0))

    # ----------------------------
    # RUN
    # ----------------------------
    def start(self):
        self.running = True

        self.exporter.write_meta(
            mode="FREE_ROAM",
            sample_ms=self.sample_ms_active,
            root_screen_w=0,
            root_screen_h=0,
            window_w=0,
            window_h=0,
            dpi=1.0,
            protocol={"type": "free_roam"}
        )

        self.log_event("session_start")

        while self.running:
            self._sample_once()

        self._finalize()

    def stop(self):
        self.running = False

    def _finalize(self):
        self.exporter.write_points(self.points)
        self.exporter.write_dict_rows(self.exporter.events_csv, self.events)
        self.exporter.write_dict_rows(self.exporter.trials_csv, self.segments)
        self.log_event("session_end")


def main():
    rec = FreeRoamRecorder()
    print("🔥 FREE ROAM running — ESC not bound here, ctrl+c to stop")
    rec.start()


if __name__ == "__main__":
    main()