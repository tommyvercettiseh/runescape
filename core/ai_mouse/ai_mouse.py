from __future__ import annotations

import os
import time
import random
import json
from typing import Optional, Tuple, Literal, Protocol

from pynput.mouse import Controller, Button

from .ai_mouse_settings import MOUSE_PROFILE, load_master_profile
from . import ai_mouse_movement as movement
from .ai_mouse_movement import (
    plan_move,
    get_default_bounds,
    clamp_point,
    CursorMotionConfig,
)

MouseButton = Literal["left", "right"]
ClickMode = Literal["hold", "tap", "safe_tap"]
ScrollDir = Literal["up", "down"]

Point = Tuple[int, int]
Bounds = Tuple[int, int, int, int]


_DEFAULT_MOUSE = Controller()

_ENERGY = 0.55  # 0..1 (lichte drift)
_LAST_ACTION_TS = 0.0

_SESSION_BIAS = (0, 0)
_SESSION_BIAS_EXPIRY = 0.0

_RHYTHM_MODES = {
    "focused": (5.0, 12.0),
    "relaxed": (12.0, 25.0),
    "distracted": (20.0, 45.0),
    "hyper": (2.0, 6.0),
}
_RHYTHM_STATE = {"mode": "focused", "next_switch": 0.0}


# ============================================================
# MouseLab → MOUSE_PROFILE mapper
# ============================================================

def _maybe_load_mouselab_profile(path: str) -> bool:
    """
    Supports MouseLab profile_preview.json structure.
    We map MouseLab globals into MOUSE_PROFILE keys (movement + timing).

    MouseLab expected keys (globals):
      median_speed_px_s: {p50, p90}
      overshoot_px: {p50, p90}
      pre_click_ms: {p50}
      click_hold_ms: {p50}
      tail_time_ms: {p50}
      stop_time_ms: {p50}
      jerk_p90: {p90} (optional)
      curv_p90: {p90} (optional)
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        g = data.get("globals") or {}
        if not isinstance(g, dict) or not g:
            return False

        def gp(name: str, key: str, default: float) -> float:
            d = g.get(name) or {}
            if not isinstance(d, dict):
                return default
            v = d.get(key, default)
            try:
                return float(v)
            except Exception:
                return default

        speed_p50 = gp("median_speed_px_s", "p50", 950.0)
        speed_p90 = gp("median_speed_px_s", "p90", 1600.0)

        over_p50 = gp("overshoot_px", "p50", 8.0)
        over_p90 = gp("overshoot_px", "p90", 20.0)

        pre_click_s = gp("pre_click_ms", "p50", 85.0) / 1000.0
        click_hold_s = gp("click_hold_ms", "p50", 35.0) / 1000.0
        tail_s = gp("tail_time_ms", "p50", 80.0) / 1000.0
        stop_s = gp("stop_time_ms", "p50", 40.0) / 1000.0

        settle_s = max(0.02, min(0.25, (tail_s * 0.65) + (stop_s * 0.35)))

        jerk90 = gp("jerk_p90", "p90", 0.0)
        curv90 = gp("curv_p90", "p90", 0.0)

        # movement bounds
        MOUSE_PROFILE["speed_min"] = max(200.0, speed_p50 * 0.78)
        MOUSE_PROFILE["speed_max"] = max(float(MOUSE_PROFILE["speed_min"]) + 80.0, speed_p90 * 1.05)

        MOUSE_PROFILE["overshoot_min"] = max(1.0, over_p50 * 0.70)
        MOUSE_PROFILE["overshoot_max"] = max(float(MOUSE_PROFILE["overshoot_min"]) + 1.0, over_p90 * 1.15)

        # click + settle
        MOUSE_PROFILE["pre_click_s"] = max(0.0, min(0.45, pre_click_s))
        MOUSE_PROFILE["click_hold_s"] = max(0.006, min(0.30, click_hold_s))
        MOUSE_PROFILE["settle_s"] = settle_s

        if "close_px" not in MOUSE_PROFILE or MOUSE_PROFILE["close_px"] is None:
            MOUSE_PROFILE["close_px"] = 2.2

        # optional tremor
        base = 0.16
        add = min(0.18, (abs(jerk90) * 0.00025) + (abs(curv90) * 0.08))
        MOUSE_PROFILE["micro_tremor_max"] = max(0.08, min(0.34, base + add))

        return True
    except Exception:
        return False


_PROFILE_LOADED = False

def _auto_load_profile_once() -> None:
    global _PROFILE_LOADED
    if _PROFILE_LOADED:
        return

    path = os.getenv("AI_CURSOR_PROFILE", "").strip()
    if not path:
        path = "master_profile.json"

    try:
        if os.path.exists(path):
            ok = _maybe_load_mouselab_profile(path)
            if not ok:
                load_master_profile(path)

        # tune movement engine from profile
        movement.apply_profile_tuning(MOUSE_PROFILE)
    except Exception:
        pass

    _PROFILE_LOADED = True


_auto_load_profile_once()

print("AI Mouse profile loaded:",
      MOUSE_PROFILE.get("speed_min"),
      MOUSE_PROFILE.get("speed_max"),
      MOUSE_PROFILE.get("overshoot_min"),
      MOUSE_PROFILE.get("overshoot_max"))


# ============================================================
# EXECUTOR (pynput)
# ============================================================

class MouseExecutor(Protocol):
    def position(self) -> Point: ...
    def move_to(self, x: int, y: int) -> None: ...
    def click(self, button: MouseButton = "left", mode: ClickMode = "tap",
              hold_s: Optional[float] = None) -> None: ...
    def scroll(self, direction: ScrollDir, amount: int = 1) -> None: ...


class PynputExecutor:
    def __init__(self, mouse: Optional[Controller] = None):
        self.mouse = mouse or _DEFAULT_MOUSE

    def position(self) -> Point:
        x, y = self.mouse.position
        return int(x), int(y)

    def move_to(self, x: int, y: int) -> None:
        self.mouse.position = (int(x), int(y))

    def click(self, button: MouseButton = "left", mode: ClickMode = "tap",
              hold_s: Optional[float] = None) -> None:
        btn = Button.left if button == "left" else Button.right

        if mode == "tap":
            self.mouse.press(btn)
            time.sleep(0.001)
            self.mouse.release(btn)
            return

        if mode == "safe_tap":
            self.mouse.press(btn)
            time.sleep(random.uniform(0.018, 0.055))
            self.mouse.release(btn)
            return

        self.mouse.press(btn)
        time.sleep(float(hold_s) if hold_s is not None else float(MOUSE_PROFILE.get("click_hold_s", 0.03)))
        self.mouse.release(btn)

    def scroll(self, direction: ScrollDir, amount: int = 1) -> None:
        dy = amount if direction == "down" else -amount
        self.mouse.scroll(0, dy)


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _now() -> float:
    return time.perf_counter()

def _sleep(s: float) -> None:
    time.sleep(max(0.0, float(s)))

def _rand(a: float, b: float) -> float:
    return random.uniform(float(a), float(b))

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(float(lo), min(float(hi), float(v)))

def _choose_rhythm_delay() -> float:
    t = _now()
    if _RHYTHM_STATE["next_switch"] <= t:
        _RHYTHM_STATE["mode"] = random.choice(list(_RHYTHM_MODES.keys()))
        _RHYTHM_STATE["next_switch"] = t + random.uniform(12.0, 26.0)
    lo, hi = _RHYTHM_MODES[_RHYTHM_STATE["mode"]]
    return random.uniform(lo, hi) / 1000.0

def _update_energy() -> None:
    global _ENERGY, _LAST_ACTION_TS
    t = _now()
    if _LAST_ACTION_TS == 0.0:
        _LAST_ACTION_TS = t
        return
    dt = t - _LAST_ACTION_TS
    _LAST_ACTION_TS = t
    _ENERGY = _clamp(_ENERGY - dt * 0.00008, 0.15, 1.0)

def _session_bias() -> Tuple[int, int]:
    global _SESSION_BIAS, _SESSION_BIAS_EXPIRY
    t = _now()
    if t >= _SESSION_BIAS_EXPIRY:
        _SESSION_BIAS = (random.randint(-2, 2), random.randint(-2, 2))
        _SESSION_BIAS_EXPIRY = t + random.uniform(8.0, 18.0)
    return _SESSION_BIAS


# ============================================================
# PUBLIC API
# ============================================================

def human_move_to(
    x: int,
    y: int,
    *,
    executor: Optional[MouseExecutor] = None,
    bounds: Optional[Bounds] = None,
    config: Optional[CursorMotionConfig] = None,
    clamp: bool = True,
) -> None:
    """
    Move the mouse using your planner (ai_mouse_movement).
    Supports MouseLab profile_preview.json via AI_CURSOR_PROFILE.
    """
    _update_energy()
    ex = executor or PynputExecutor()
    bx = bounds or get_default_bounds()

    sx, sy = ex.position()
    tx, ty = int(x), int(y)

    ox, oy = _session_bias()
    tx += ox
    ty += oy

    if clamp:
        tx, ty = clamp_point((tx, ty), bx)

    steps = plan_move((sx, sy), (tx, ty), bounds=bx, config=config)
    for st in steps:
        ex.move_to(st.x, st.y)
        _sleep(st.dt)

    settle_s = float(MOUSE_PROFILE.get("settle_s", 0.08))
    settle_s *= (1.0 + (1.0 - _ENERGY) * 0.25)
    _sleep(_rand(settle_s * 0.55, settle_s * 1.15))


def human_click(
    button: MouseButton = "left",
    *,
    executor: Optional[MouseExecutor] = None,
    mode: ClickMode = "safe_tap",
) -> None:
    ex = executor or PynputExecutor()
    pre = float(MOUSE_PROFILE.get("pre_click_s", 0.10))
    _sleep(_rand(pre * 0.6, pre * 1.25))
    ex.click(button=button, mode=mode, hold_s=float(MOUSE_PROFILE.get("click_hold_s", 0.03)))


# ============================================================
# MAIN TEST
# ============================================================

def main_test(n: int = 25, margin: int = 90):
    print("\n🧪 AI Mouse MAIN TEST\n")
    ex = PynputExecutor()
    bounds = get_default_bounds()

    x1, y1, x2, y2 = bounds
    x1 += margin
    y1 += margin
    x2 -= margin
    y2 -= margin

    print("Bounds (primary):", bounds)
    print("Config: n=", n, "margin=", margin)

    for _ in range(n):
        tx = random.randint(x1, x2)
        ty = random.randint(y1, y2)

        human_move_to(tx, ty, executor=ex, bounds=bounds)
        human_click(executor=ex, mode="safe_tap")

        _sleep(_choose_rhythm_delay())

    print("\n✅ Done.\n")


if __name__ == "__main__":
    main_test()