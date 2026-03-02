from __future__ import annotations

import random
from typing import Any, Dict, Optional, Tuple

from .config import (
    TOPBAR_H,
    PHASE1_REPS, PHASE2_REPS, PHASE3_BLOCKS,
    SIZE_BASE, SIZE_SWEEP, SIZE_SMALL,
    PINK, HIT_GREEN, MISS_RED, BASE_BLUE,
)
from .features import now, dist


class TaskRunner:
    def __init__(self, canvas):
        self.canvas = canvas

        self.canvas_w = int(canvas.winfo_width()) if canvas.winfo_width() > 1 else 1000
        self.canvas_h = int(canvas.winfo_height()) if canvas.winfo_height() > 1 else 800

        self.phase = 1
        self.phase_progress = 0
        self.phase_goal = {1: PHASE1_REPS, 2: PHASE2_REPS, 3: PHASE3_BLOCKS}

        self.base_target: Optional[Dict[str, Any]] = None
        self.active_targets: Dict[int, Dict[str, Any]] = {}
        self.current_trial_id = 0

        self._awaiting_base_click = True
        self._awaiting_target_click = False
        self._phase3_remaining = set()

        self._create_base()

    def on_resize(self, w: int, h: int) -> None:
        self.canvas_w = int(w)
        self.canvas_h = int(h)
        self._reposition_base()

    def _base_center(self) -> Tuple[float, float]:
        return (self.canvas_w / 2, (self.canvas_h - TOPBAR_H) / 2 + TOPBAR_H)

    def _inside(self, t: Dict[str, Any], x: int, y: int) -> bool:
        return (t["x1"] <= x <= t["x2"]) and (t["y1"] <= y <= t["y2"])

    def nearest_active_target(self, mouse_x: int, mouse_y: int) -> Optional[Dict[str, Any]]:
        if not self.active_targets:
            return None
        m0 = (mouse_x, mouse_y)
        best = None
        best_d = 1e18
        for t in self.active_targets.values():
            d = dist(m0, t["center"])
            if d < best_d:
                best_d = d
                best = t
        return best

    def _next_trial_id(self) -> int:
        self.current_trial_id += 1
        return self.current_trial_id

    def _create_base(self) -> None:
        cx, cy = self._base_center()
        s = SIZE_BASE
        x1 = int(cx - s / 2); y1 = int(cy - s / 2)
        x2 = x1 + s; y2 = y1 + s
        cid = self.canvas.create_rectangle(x1, y1, x2, y2, fill=BASE_BLUE, outline="")
        self.base_target = {
            "canvas_id": cid,
            "trial_id": 0,
            "label": "BASE",
            "size": s,
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "center": ((x1 + x2)/2, (y1 + y2)/2),
            "spawn_ts": now(),
            "start_xy": (cx, cy),
            "difficulty": 0.0,
            "miss_clicks": 0,
            "start_point_index": 0,
            "first_enter_ts": None,
            "click_down_ts": None,
            "click_up_ts": None,
            "phase": 0,
        }

    def _reposition_base(self) -> None:
        if not self.base_target:
            return
        cx, cy = self._base_center()
        s = self.base_target["size"]
        x1 = int(cx - s / 2); y1 = int(cy - s / 2)
        x2 = x1 + s; y2 = y1 + s
        self.base_target.update({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "center": ((x1 + x2)/2, (y1 + y2)/2),
        })
        self.canvas.coords(self.base_target["canvas_id"], x1, y1, x2, y2)

    def clear_targets(self) -> None:
        for cid in list(self.active_targets.keys()):
            try:
                self.canvas.delete(cid)
            except Exception:
                pass
            self.active_targets.pop(cid, None)

    def add_target(self, cx: float, cy: float, size: int, label: str,
                   *, start_point_index: int, mouse_x: int, mouse_y: int) -> Dict[str, Any]:
        x1 = int(cx - size / 2); y1 = int(cy - size / 2)
        x2 = x1 + size; y2 = y1 + size
        cid = self.canvas.create_rectangle(x1, y1, x2, y2, fill=PINK, outline="")
        center = ((x1 + x2) / 2, (y1 + y2) / 2)
        spawn_ts = now()
        trial_id = self._next_trial_id()

        t = {
            "canvas_id": cid,
            "trial_id": trial_id,
            "label": label,
            "size": size,
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "center": center,
            "spawn_ts": spawn_ts,
            "start_xy": (mouse_x, mouse_y),
            "difficulty": (dist((mouse_x, mouse_y), center) / max(1, size)),
            "miss_clicks": 0,
            "start_point_index": start_point_index,
            "first_enter_ts": None,
            "click_down_ts": None,
            "click_up_ts": None,
            "phase": int(self.phase),
        }
        self.active_targets[cid] = t
        return t

    def advance_phase(self, *, forced: bool = False) -> str:
        self.clear_targets()
        self.phase_progress = 0
        self._awaiting_base_click = True
        self._awaiting_target_click = False
        self._phase3_remaining = set()

        if self.phase < 3:
            self.phase += 1
            return "PHASE_CHANGED"
        return "END"

    def spawn_phase_target(self, *, start_point_index: int, mouse_x: int, mouse_y: int) -> None:
        if self.phase == 1:
            self._spawn_phase1_target(start_point_index=start_point_index, mouse_x=mouse_x, mouse_y=mouse_y)
        elif self.phase == 2:
            self._spawn_phase2_target(start_point_index=start_point_index, mouse_x=mouse_x, mouse_y=mouse_y)
        else:
            self._spawn_phase3_blocks(start_point_index=start_point_index, mouse_x=mouse_x, mouse_y=mouse_y)

    def _spawn_phase1_target(self, *, start_point_index: int, mouse_x: int, mouse_y: int) -> None:
        pad = 90
        cx = random.uniform(pad, self.canvas_w - pad)
        cy = random.uniform(TOPBAR_H + pad, self.canvas_h - pad)
        self.add_target(cx, cy, SIZE_SWEEP, "P1_TARGET", start_point_index=start_point_index, mouse_x=mouse_x, mouse_y=mouse_y)
        self._awaiting_target_click = True

    def _phase2_positions(self):
        pad = 70
        cx0, cy0 = self._base_center()
        left = (pad, cy0)
        right = (self.canvas_w - pad, cy0)
        top = (cx0, TOPBAR_H + pad)
        bottom = (cx0, self.canvas_h - pad)
        tl = (pad, TOPBAR_H + pad)
        tr = (self.canvas_w - pad, TOPBAR_H + pad)
        bl = (pad, self.canvas_h - pad)
        br = (self.canvas_w - pad, self.canvas_h - pad)
        return [left, right, top, bottom, tl, tr, bl, br]

    def _spawn_phase2_target(self, *, start_point_index: int, mouse_x: int, mouse_y: int) -> None:
        seq = self._phase2_positions()
        idx = self.phase_progress % len(seq)
        cx, cy = seq[idx]
        self.add_target(cx, cy, SIZE_SWEEP, "P2_SWEEP", start_point_index=start_point_index, mouse_x=mouse_x, mouse_y=mouse_y)
        self._awaiting_target_click = True

    def _spawn_phase3_blocks(self, *, start_point_index: int, mouse_x: int, mouse_y: int) -> None:
        self.clear_targets()
        pad = 70

        xs_top = [pad + i * (self.canvas_w - 2 * pad) / 5 for i in range(1, 5)]
        ys_left = [TOPBAR_H + pad + i * (self.canvas_h - TOPBAR_H - 2 * pad) / 5 for i in range(1, 5)]

        positions = []
        for x in xs_top:
            positions.append((x, TOPBAR_H + pad))
        for x in xs_top:
            positions.append((x, self.canvas_h - pad))
        for y in ys_left:
            positions.append((pad, y))
        for y in ys_left:
            positions.append((self.canvas_w - pad, y))

        random.shuffle(positions)
        positions = positions[:PHASE3_BLOCKS]

        for cx, cy in positions:
            t = self.add_target(cx, cy, SIZE_SMALL, "P3_BLOCK",
                                start_point_index=start_point_index, mouse_x=mouse_x, mouse_y=mouse_y)
            self._phase3_remaining.add(t["trial_id"])

        self._awaiting_target_click = True

    def on_left_down(self, *, running: bool, mouse_x: int, mouse_y: int, start_point_index: int) -> Dict[str, Any]:
        out: Dict[str, Any] = {"kind": "down", "hit": False, "target": None, "base": False, "misclick": False}

        if self.base_target and self._inside(self.base_target, mouse_x, mouse_y):
            out["base"] = True
            out["target"] = self.base_target

            if running and self.phase in (1, 2) and self._awaiting_base_click:
                self._awaiting_base_click = False
                self.spawn_phase_target(start_point_index=start_point_index, mouse_x=mouse_x, mouse_y=mouse_y)
            return out

        target = self.nearest_active_target(mouse_x, mouse_y)
        out["target"] = target

        if target and self._inside(target, mouse_x, mouse_y):
            target["click_down_ts"] = now()
            if running:
                out["hit"] = True
            return out

        out["misclick"] = True
        if target:
            target["miss_clicks"] += 1
            try:
                self.canvas.itemconfig(target["canvas_id"], fill=MISS_RED)
                self.canvas.after(90, lambda cid=target["canvas_id"]: self.canvas.itemconfig(cid, fill=PINK))
            except Exception:
                pass
        return out

    def on_left_up(self, *, mouse_x: int, mouse_y: int) -> Optional[Dict[str, Any]]:
        target = self.nearest_active_target(mouse_x, mouse_y)
        if target and self._inside(target, mouse_x, mouse_y):
            target["click_up_ts"] = now()
            return target
        return None

    def finalize_hit(self, target: Dict[str, Any]) -> None:
        cid = target["canvas_id"]
        try:
            self.canvas.itemconfig(cid, fill=HIT_GREEN)
            self.canvas.after(80, lambda: self.canvas.delete(cid))
        except Exception:
            pass

        self.active_targets.pop(cid, None)

        if self.phase in (1, 2):
            self.phase_progress += 1
            self._awaiting_base_click = True
            self._awaiting_target_click = False
        else:
            self.phase_progress += 1
            if target["trial_id"] in self._phase3_remaining:
                self._phase3_remaining.remove(target["trial_id"])

        if self.phase in (1, 2) and self.phase_progress >= self.phase_goal[self.phase]:
            self.advance_phase()

        if self.phase == 3:
            if self.phase_progress >= self.phase_goal[3] or not self._phase3_remaining:
                self.advance_phase()
            elif not self.active_targets:
                self._spawn_phase3_blocks(
                    start_point_index=target["start_point_index"],
                    mouse_x=int(target["center"][0]),
                    mouse_y=int(target["center"][1]),
                )