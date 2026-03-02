from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from .config import SAMPLE_MS, MOVE_EVENT_EVERY_N
from .features import now, angle_diff, dist


Point = Tuple[Any, ...]


class Recorder:
    def __init__(
        self,
        root,
        canvas,
        *,
        get_nearest_target: Callable[[int, int], Optional[Dict[str, Any]]],
        is_inside_target: Callable[[Dict[str, Any], int, int], bool],
        on_left_down_task: Callable[[bool, int, int, int], Dict[str, Any]],
        on_left_up_task: Callable[[int, int], Optional[Dict[str, Any]]],
        session_id: str,
        mode: str,
        sample_ms: int = SAMPLE_MS,
        move_event_every_n: int = MOVE_EVENT_EVERY_N,
    ):
        self.root = root
        self.canvas = canvas

        self.get_nearest_target = get_nearest_target
        self.is_inside_target = is_inside_target
        self.on_left_down_task = on_left_down_task
        self.on_left_up_task = on_left_up_task

        self.session_id = session_id
        self.mode = mode
        self.sample_ms = int(sample_ms)
        self.move_event_every_n = int(move_event_every_n)

        self.running = False
        self.session_start: Optional[float] = None

        self.mouse_x = 0
        self.mouse_y = 0
        self.buttons = 0
        self.current_click_id = 0

        self.points: List[Point] = []
        self.events: List[Dict[str, Any]] = []

        self.last_sample_ts: Optional[float] = None
        self.last_sample_xy: Optional[Tuple[int, int]] = None
        self._move_event_counter = 0

        self._last_vx = 0.0
        self._last_vy = 0.0
        self._last_ax = 0.0
        self._last_ay = 0.0
        self._last_heading = 0.0

        self._down_ts: Optional[float] = None

        self._bind_events()

    def _mouse_in_canvas(self, x_root: int, y_root: int) -> Tuple[int, int]:
        x = x_root - self.canvas.winfo_rootx()
        y = y_root - self.canvas.winfo_rooty()
        x = max(0, min(int(x), int(self.canvas.winfo_width())))
        y = max(0, min(int(y), int(self.canvas.winfo_height())))
        return x, y

    def _bind_events(self) -> None:
        self.root.bind("<Motion>", self.on_motion_root)
        self.root.bind("<ButtonPress-1>", self.on_l_down_root)
        self.root.bind("<ButtonRelease-1>", self.on_l_up_root)

        self.root.bind("<KeyPress-space>", lambda e: self.toggle_run())
        self.root.bind("<KeyPress-Escape>", lambda e: self.finish_request())

        self._finish_request_cb: Optional[Callable[[], None]] = None

    def set_finish_request_callback(self, cb: Callable[[], None]) -> None:
        self._finish_request_cb = cb

    def finish_request(self) -> None:
        if self._finish_request_cb:
            self._finish_request_cb()

    def log_event(self, event_type: str, *, button: str = "", target: Optional[Dict[str, Any]] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        tstamp = now()
        row = {
            "session_id": self.session_id,
            "t": round(tstamp, 6),
            "x": int(self.mouse_x),
            "y": int(self.mouse_y),
            "event_type": event_type,
            "buttons": int(self.buttons),
            "button": button,
            "click_id": str(self.current_click_id) if self.current_click_id else "",
            "target_id": str(target["trial_id"]) if target else "",
            "label": str(target["label"]) if target else "",
            "phase": int(target["phase"]) if target and "phase" in target else "",
            "extra": json.dumps(extra or {}, ensure_ascii=False),
        }
        self.events.append(row)

    def toggle_run(self) -> None:
        if not self.running:
            self.running = True
            if self.session_start is None:
                self.session_start = now()
                self.log_event("session_start", extra={"mode": self.mode})
            else:
                self.log_event("session_resume")

            self.last_sample_ts = None
            self.last_sample_xy = None
            self.sample_loop()
        else:
            self.running = False
            self.log_event("session_pause")

    def on_motion_root(self, e) -> None:
        cx, cy = self._mouse_in_canvas(e.x_root, e.y_root)
        self.mouse_x, self.mouse_y = cx, cy

    def on_l_down_root(self, e) -> None:
        cx, cy = self._mouse_in_canvas(e.x_root, e.y_root)
        self.mouse_x, self.mouse_y = cx, cy
        self._handle_left_down()

    def on_l_up_root(self, e) -> None:
        cx, cy = self._mouse_in_canvas(e.x_root, e.y_root)
        self.mouse_x, self.mouse_y = cx, cy
        self._handle_left_up()

    def _handle_left_down(self) -> None:
        self.buttons = 1
        self.current_click_id += 1
        self._down_ts = now()

        out = self.on_left_down_task(self.running, self.mouse_x, self.mouse_y, len(self.points))
        target = out.get("target")

        self.log_event("down", button="left", target=target)

        if out.get("misclick"):
            self.log_event("misclick", target=target)

    def _handle_left_up(self) -> None:
        hold_ms = ""
        if self._down_ts is not None:
            hold_ms = round((now() - self._down_ts) * 1000.0, 3)

        target = self.on_left_up_task(self.mouse_x, self.mouse_y)
        self.log_event("up", button="left", target=target, extra={"hold_ms": hold_ms})
        self.buttons = 0

    def sample_loop(self) -> None:
        if not self.running:
            return

        ts = now()

        if self.last_sample_ts is None:
            dt = 0.0
            dt_ms = 0.0
        else:
            dt = ts - self.last_sample_ts
            dt_ms = dt * 1000.0

        if self.last_sample_xy is None or dt <= 0:
            dx = dy = 0.0
            vx = vy = 0.0
            ax = ay = 0.0
            jerk = 0.0
            heading = self._last_heading
            dheading = 0.0
            curv = 0.0
        else:
            dx = float(self.mouse_x - self.last_sample_xy[0])
            dy = float(self.mouse_y - self.last_sample_xy[1])
            vx = dx / dt
            vy = dy / dt

            ax = (vx - self._last_vx) / dt
            ay = (vy - self._last_vy) / dt

            jx = (ax - self._last_ax) / dt
            jy = (ay - self._last_ay) / dt
            jerk = (jx * jx + jy * jy) ** 0.5

            speed_step = (vx * vx + vy * vy) ** 0.5
            if speed_step > 1e-9:
                import math
                heading = math.atan2(vy, vx)
                dheading = angle_diff(heading, self._last_heading)
                ds = (dx * dx + dy * dy) ** 0.5
                curv = abs(dheading) / max(1e-6, ds)
            else:
                heading = self._last_heading
                dheading = 0.0
                curv = 0.0

        import math
        speed = math.hypot(vx, vy)
        accel = math.hypot(ax, ay)

        self.last_sample_ts = ts
        self.last_sample_xy = (self.mouse_x, self.mouse_y)
        self._last_vx, self._last_vy = vx, vy
        self._last_ax, self._last_ay = ax, ay
        self._last_heading = heading

        target = self.get_nearest_target(self.mouse_x, self.mouse_y)
        if target:
            cx, cy = target["center"]
            dist_t = dist((self.mouse_x, self.mouse_y), (cx, cy))
            inside = 1 if self.is_inside_target(target, self.mouse_x, self.mouse_y) else 0
            if inside and target.get("first_enter_ts") is None:
                target["first_enter_ts"] = ts
        else:
            cx = cy = 0.0
            dist_t = 0.0
            inside = 0

        active_trial = target["trial_id"] if target else ""

        self.points.append((
            ts, int(self.mouse_x), int(self.mouse_y), int(self.buttons), active_trial,
            float(dt_ms), float(vx), float(vy), float(speed),
            float(ax), float(ay), float(accel), float(jerk),
            float(heading), float(dheading), float(curv),
            float(dist_t), int(inside),
            int(target["trial_id"]) if target else "",
            str(target["label"]) if target else "",
            float(cx), float(cy),
            int(target["size"]) if target else "",
        ))

        self._move_event_counter += 1
        if (self._move_event_counter % self.move_event_every_n) == 0:
            self.log_event("move", target=target)

        self.root.after(self.sample_ms, self.sample_loop)