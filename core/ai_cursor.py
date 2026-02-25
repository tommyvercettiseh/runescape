# core/ai_cursor.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Tuple
import os
import random
import time
import sys

from core.ai_cursor_movement import CursorMotionConfig, plan_move, Point, Bounds


# ============================================================
# Executor (moving the real mouse)
# ============================================================

class MouseExecutor:
    def move(self, x: int, y: int) -> None:
        raise NotImplementedError

    def position(self) -> Point:
        raise NotImplementedError

    def click_left(self) -> None:
        raise NotImplementedError


class PyAutoGuiExecutor(MouseExecutor):
    def __init__(self) -> None:
        import pyautogui
        self.pg = pyautogui
        self.pg.FAILSAFE = False

    def move(self, x: int, y: int) -> None:
        self.pg.moveTo(int(x), int(y))

    def position(self) -> Point:
        p = self.pg.position()
        return (int(p.x), int(p.y))

    def click_left(self) -> None:
        self.pg.click()


class Win32Executor(MouseExecutor):
    def __init__(self) -> None:
        import ctypes
        self.ct = ctypes

    def move(self, x: int, y: int) -> None:
        self.ct.windll.user32.SetCursorPos(int(x), int(y))

    def position(self) -> Point:
        import ctypes
        pt = ctypes.wintypes.POINT()
        self.ct.windll.user32.GetCursorPos(self.ct.byref(pt))
        return (int(pt.x), int(pt.y))

    def click_left(self) -> None:
        import ctypes
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        self.ct.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        self.ct.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def get_default_executor() -> MouseExecutor:
    # prefer pyautogui if available, else fallback win32 on Windows
    try:
        return PyAutoGuiExecutor()
    except Exception:
        if os.name == "nt":
            return Win32Executor()
        raise RuntimeError("Geen executor beschikbaar. Installeer pyautogui of draai op Windows.")


# ============================================================
# Core API
# ============================================================

def move_to(
    pos: Point,
    *,
    motion: Optional[CursorMotionConfig] = None,
    bounds: Optional[Bounds] = None,
    executor: Optional[MouseExecutor] = None,
    speed_pct: float = 100.0,
    scenario_label: Optional[str] = None,
) -> Point:
    """
    Orchestrator: plans path then executes it at real time pace.
    speed_pct scales duration (higher is faster).
    """
    ex = executor or get_default_executor()
    start = ex.position()

    m = motion or CursorMotionConfig()

    # apply speed scaling
    sp = max(10.0, min(250.0, float(speed_pct)))
    duration = float(m.duration) * (100.0 / sp)

    m_eff = CursorMotionConfig(
        duration=duration,
        fps=m.fps,
        min_steps=m.min_steps,
        min_duration=m.min_duration,
        overshoot_chance=m.overshoot_chance,
        overshoot_px_mean=m.overshoot_px_mean,
        overshoot_px_sd=m.overshoot_px_sd,
        micro_jitter_px=m.micro_jitter_px,
        endpoint_settle_ms=m.endpoint_settle_ms,
        tremor_strength=m.tremor_strength,
        fatigue_strength=m.fatigue_strength,
    )

    path = plan_move(start, (int(pos[0]), int(pos[1])), m_eff, bounds=bounds)

    # execute with timing
    steps = max(2, len(path))
    total_s = max(m_eff.min_duration, m_eff.duration)
    dt = total_s / (steps - 1)

    t0 = time.perf_counter()
    for i, (x, y) in enumerate(path):
        ex.move(x, y)

        # sleep to match target timeline
        next_t = t0 + (i * dt)
        now = time.perf_counter()
        sl = next_t - now
        if sl > 0:
            time.sleep(sl)

    # tiny endpoint settle (doesn't change position, only timing)
    if m_eff.endpoint_settle_ms > 0:
        time.sleep(m_eff.endpoint_settle_ms / 1000.0)

    return ex.position()


# legacy compatibility for older helpers
def move_cursor(
    pos: Point,
    *,
    config: Optional[CursorMotionConfig] = None,
    motion: Optional[CursorMotionConfig] = None,
    bounds: Optional[Bounds] = None,
    executor: Optional[MouseExecutor] = None,
    speed_pct: float = 100.0,
    scenario_label: Optional[str] = None,
) -> Point:
    m = motion or config or CursorMotionConfig()
    return move_to(
        pos,
        motion=m,
        bounds=bounds,
        executor=executor,
        speed_pct=speed_pct,
        scenario_label=scenario_label,
    )


def click(
    *,
    executor: Optional[MouseExecutor] = None,
) -> None:
    ex = executor or get_default_executor()
    ex.click_left()


def move_and_click(
    pos: Point,
    *,
    motion: Optional[CursorMotionConfig] = None,
    bounds: Optional[Bounds] = None,
    executor: Optional[MouseExecutor] = None,
    speed_pct: float = 100.0,
) -> Point:
    p = move_to(pos, motion=motion, bounds=bounds, executor=executor, speed_pct=speed_pct)
    click(executor=executor)
    return p


# ============================================================
# Testrun
# ============================================================

def _get_screen_bounds() -> Bounds:
    # best effort, uses pyautogui if present
    try:
        import pyautogui
        w, h = pyautogui.size()
        return (0, 0, int(w - 1), int(h - 1))
    except Exception:
        # fallback conservative
        return (0, 0, 1919, 1079)


def _demo_roam(seconds: float = 8.0) -> None:
    ex = get_default_executor()
    b = _get_screen_bounds()

    print("✅ ai_cursor testrun gestart")
    print(f"Bounds: {b}")
    print("Stoppen? Beweeg je muis naar een hoek (failsafe) als je pyautogui gebruikt 😉")

    t_end = time.time() + float(seconds)

    base = CursorMotionConfig(
        duration=0.23,
        fps=120,
        overshoot_chance=0.22,
        micro_jitter_px=0.55,
        tremor_strength=0.10,
        fatigue_strength=0.0,
    )

    while time.time() < t_end:
        x = random.randint(b[0] + 60, b[2] - 60)
        y = random.randint(b[1] + 90, b[3] - 90)

        sp = random.uniform(75, 160)
        # tiny session drift: fatigue creeps up a bit
        fatigue = min(0.35, max(0.0, (seconds - (t_end - time.time())) / seconds) * 0.35)

        motion = CursorMotionConfig(
            duration=base.duration * random.uniform(0.85, 1.20),
            fps=base.fps,
            min_steps=base.min_steps,
            min_duration=base.min_duration,
            overshoot_chance=base.overshoot_chance,
            overshoot_px_mean=base.overshoot_px_mean,
            overshoot_px_sd=base.overshoot_px_sd,
            micro_jitter_px=base.micro_jitter_px,
            endpoint_settle_ms=base.endpoint_settle_ms,
            tremor_strength=base.tremor_strength,
            fatigue_strength=fatigue,
        )

        move_to((x, y), motion=motion, bounds=b, executor=ex, speed_pct=sp)
        time.sleep(random.uniform(0.03, 0.12))

    print("✅ ai_cursor testrun klaar")


if __name__ == "__main__":
    # simpele run: python core/ai_cursor.py
    _demo_roam(seconds=10.0)