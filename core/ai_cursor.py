from __future__ import annotations

import os
import time
import random
from dataclasses import dataclass
from typing import Optional, Tuple, Literal, Protocol
import math
import ctypes

from pynput.mouse import Controller, Button

from core.ai_cursor_settings import (
    mouse_profile as MOUSE_PROFILE,
    load_master_profile,
)

import core.ai_cursor_movement as movement

from core.ai_cursor_movement import (
    plan_move,
    get_default_bounds,
    clamp_point,
    CursorMotionConfig,
    PlannedStep,
)

MouseButton = Literal["left", "right"]
ClickMode = Literal["hold", "tap", "safe_tap"]
ScrollDir = Literal["up", "down"]

Point = Tuple[int, int]
Bounds = Tuple[int, int, int, int]

_DEFAULT_MOUSE = Controller()
_HAND_BIAS = random.uniform(-1.0, 1.0)
_SESSION_BIAS = (0, 0)
_SESSION_BIAS_EXPIRY = 0.0

_ENERGY = 0.55  # 0..1
_LAST_ACTION_TS = 0.0
_IN_LOOK = False

_RHYTHM_MODES = {
    "focused": (5.0, 12.0),
    "relaxed": (12.0, 25.0),
    "distracted": (20.0, 45.0),
    "hyper": (2.0, 6.0),
}
_RHYTHM_STATE = {"mode": "focused", "next_switch": 0.0, "next_delay": 0.0}


# ============================================================
# PROFILE GETTER (safe + backward compatible)
# ============================================================
def _p(key: str, default=None):
    try:
        if isinstance(MOUSE_PROFILE, dict):
            return MOUSE_PROFILE.get(key, default)
        return getattr(MOUSE_PROFILE, key, default)
    except Exception:
        return default


# ============================================================
# AUTO LOAD MASTER PROFILE
# ============================================================
_PROFILE_LOADED = False


def _auto_load_profile_once():
    global _PROFILE_LOADED
    if _PROFILE_LOADED:
        return

    path = os.getenv("AI_CURSOR_PROFILE", "").strip()
    if not path:
        path = "master_profile.json"  # default filename

    try:
        if os.path.exists(path):
            load_master_profile(path)
            movement.apply_profile_tuning(MOUSE_PROFILE)
    except Exception:
        pass

    _PROFILE_LOADED = True


_auto_load_profile_once()

print(
    "AI Cursor profile loaded:",
    _p("speed_min"),
    _p("speed_max"),
    _p("overshoot_min"),
    _p("overshoot_max"),
)


# ============================================================
# EXECUTOR (pynput)
# ============================================================
class MouseExecutor(Protocol):
    def get_pos(self) -> Point: ...
    def move_to(self, x: int, y: int) -> None: ...
    def press(self, button: MouseButton) -> None: ...
    def release(self, button: MouseButton) -> None: ...
    def scroll(self, direction: ScrollDir, amount: int) -> None: ...


class PynputExecutor:
    def __init__(self, controller: Optional[Controller] = None):
        self.m = controller or _DEFAULT_MOUSE

    def get_pos(self) -> Point:
        p = self.m.position
        return (int(p[0]), int(p[1]))

    def move_to(self, x: int, y: int) -> None:
        self.m.position = (int(x), int(y))

    def press(self, button: MouseButton) -> None:
        self.m.press(Button.left if button == "left" else Button.right)

    def release(self, button: MouseButton) -> None:
        self.m.release(Button.left if button == "left" else Button.right)

    def scroll(self, direction: ScrollDir, amount: int) -> None:
        amt = int(amount) if direction == "up" else -int(amount)
        self.m.scroll(0, amt)


# ============================================================
# CONFIGS
# ============================================================
@dataclass(frozen=True)
class ClickConfig:
    delay: float = 0.05
    button: MouseButton = "left"

    mode: ClickMode = "hold"  # "hold", "tap", "safe_tap"
    tap_min_s: float = 0.010
    tap_max_s: float = 0.055
    lock_pos: bool = False


@dataclass(frozen=True)
class SettleConfig:
    chance: float = 0.20
    min_s: float = 0.020
    max_s: float = 0.120


@dataclass(frozen=True)
class PressConfig:
    mode: ClickMode = "hold"
    tap_min_s: float = 0.010
    tap_max_s: float = 0.055
    lock_pos: bool = False


@dataclass(frozen=True)
class RandomMouseConfig:
    chance: float = 0.0
    min_px: int = 4
    max_px: int = 22
    min_s: float = 0.05
    max_s: float = 0.20


# ============================================================
# HELPERS
# ============================================================
def _ensure_session_bias() -> Tuple[int, int]:
    global _SESSION_BIAS, _SESSION_BIAS_EXPIRY
    now = time.time()
    if now > _SESSION_BIAS_EXPIRY:
        _SESSION_BIAS = (random.randint(-1, 1), random.randint(-1, 1))
        _SESSION_BIAS_EXPIRY = now + random.uniform(6.0, 18.0)
    return _SESSION_BIAS


def _energy_update(dist: float) -> None:
    global _ENERGY, _LAST_ACTION_TS
    now = time.time()
    dt = now - _LAST_ACTION_TS if _LAST_ACTION_TS else 0.0
    _LAST_ACTION_TS = now

    recover = min(0.06, dt * 0.015)
    spend = min(0.12, (dist / 1400.0) * 0.08)

    _ENERGY = max(0.05, min(1.0, _ENERGY + recover - spend))


def _energy_modifiers() -> Tuple[float, float, float]:
    e = _ENERGY
    speed = 0.85 + e * 0.35
    overshoot = 0.85 + (1.0 - e) * 0.45
    tremor = 0.80 + (1.0 - e) * 0.55
    return (speed, overshoot, tremor)


def _maybe_rhythm_delay():
    now = time.time()
    if _RHYTHM_STATE["next_switch"] <= now:
        _RHYTHM_STATE["mode"] = random.choice(list(_RHYTHM_MODES.keys()))
        _RHYTHM_STATE["next_switch"] = now + random.uniform(12.0, 55.0)
    a, b = _RHYTHM_MODES[_RHYTHM_STATE["mode"]]
    if random.random() < 0.055:
        time.sleep(random.uniform(a, b) * 0.02)


def _maybe_lookaround(ex: MouseExecutor, bounds: Bounds):
    global _IN_LOOK
    if _IN_LOOK:
        return
    if random.random() < 0.018:
        _IN_LOOK = True
        try:
            p = ex.get_pos()
            nx = clamp_point(
                (p[0] + random.randint(-25, 25), p[1] + random.randint(-18, 18)),
                bounds,
            )
            ex.move_to(nx[0], nx[1])
            time.sleep(random.uniform(0.02, 0.08))
        finally:
            _IN_LOOK = False


def _bend_point(a: Point, b: Point, bounds: Bounds, min_px: int, max_px: int) -> Point:
    mx = (a[0] + b[0]) / 2
    my = (a[1] + b[1]) / 2
    ang = random.uniform(0.9, 1.4) * (3.14159265 / 2)
    mag = random.randint(min_px, max_px)
    mx += int(round(math.cos(ang) * mag))
    my += int(round(math.sin(ang) * mag))
    return clamp_point((mx, my), bounds)


def _run_steps(
    ex: MouseExecutor,
    steps: list[PlannedStep],
    *,
    target: Point,
    settle_before: float = 0.0,
    log_metrics: bool = False,
    close_px: float = 2.0,
    settle_on_hit_range: Tuple[float, float] = (0.04, 0.09),
) -> None:
    if settle_before > 0:
        time.sleep(settle_before)

    for s in steps:
        ex.move_to(s.x, s.y)
        time.sleep(max(0.001, s.dt))

        dx = target[0] - s.x
        dy = target[1] - s.y
        if (dx * dx + dy * dy) ** 0.5 <= close_px:
            time.sleep(random.uniform(*settle_on_hit_range))
            break


def _sample_settle_delay(cfg: SettleConfig) -> float:
    if random.random() < float(cfg.chance):
        return random.uniform(float(cfg.min_s), float(cfg.max_s))
    return 0.0


def click(
    *,
    button: MouseButton | None = None,
    config: ClickConfig = ClickConfig(),
    press: PressConfig = PressConfig(),
    controller: Optional[Controller] = None,
    executor: Optional[MouseExecutor] = None,
):
    ex = executor or PynputExecutor(controller)
    btn = button or config.button

    # profile tweak: shift basic delay if provided
    delay = max(0.0, float(_p("pre_click_s", config.delay)))
    time.sleep(delay)

    mode = press.mode or config.mode
    if mode == "hold":
        ex.press(btn)
        time.sleep(random.uniform(0.018, 0.055))
        ex.release(btn)
        return

    tap_min = float(press.tap_min_s if press.tap_min_s else config.tap_min_s)
    tap_max = float(press.tap_max_s if press.tap_max_s else config.tap_max_s)

    # profile tweak: use click_hold_s if present
    hold = _p("click_hold_s", None)
    if hold is not None:
        hold = float(hold)
        tap_min = max(0.006, min(0.18, hold * 0.75))
        tap_max = max(tap_min + 0.003, min(0.22, hold * 1.25))

    ex.press(btn)
    time.sleep(random.uniform(tap_min, tap_max))
    if (mode == "safe_tap") and config.lock_pos:
        p = ex.get_pos()
        ex.move_to(p[0], p[1])
    ex.release(btn)


def move_cursor(
    pos: Point,
    *,
    config: CursorMotionConfig = CursorMotionConfig(),
    controller: Optional[Controller] = None,
    bounds: Optional[Bounds] = None,
    executor: Optional[MouseExecutor] = None,
    speed_pct: float = 100.0,
    log_metrics: bool = False,
) -> Point:
    ex = executor or PynputExecutor(controller)

    if bounds is None:
        bounds = get_default_bounds()

    _maybe_rhythm_delay()
    _maybe_lookaround(ex, bounds)

    bx, by = _ensure_session_bias()
    target = clamp_point((int(pos[0]) + bx, int(pos[1]) + by), bounds)
    start = clamp_point(ex.get_pos(), bounds)
    dx = target[0] - start[0]
    dy = target[1] - start[1]
    dist = ((dx * dx) + (dy * dy)) ** 0.5

    _energy_update(dist)
    speed_mult, _, _ = _energy_modifiers()
    speed_pct = float(speed_pct) * speed_mult

    if dist < 8.0:
        steps: list[PlannedStep] = []
        mini = max(2, min(3, int(dist) or 2))
        for i in range(1, mini + 1):
            f = i / mini
            x = int(round(start[0] + dx * f))
            y = int(round(start[1] + dy * f))
            steps.append(PlannedStep(x=x, y=y, dt=random.uniform(0.006, 0.015), tremor=0.0))

        _run_steps(ex, steps, target=target, settle_before=0.0, log_metrics=log_metrics)
        return target

    if dist > 140 and random.random() < 0.28:
        mid = _bend_point(start, target, bounds, min_px=8, max_px=42)
        steps = []
        steps.extend(plan_move(start, mid, config=config, bounds=bounds, speed_pct=speed_pct))
        steps.extend(plan_move(mid, target, config=config, bounds=bounds, speed_pct=speed_pct))
    else:
        steps = plan_move(start, target, config=config, bounds=bounds, speed_pct=speed_pct)

    _run_steps(
        ex,
        steps,
        target=target,
        settle_before=0.0,
        log_metrics=log_metrics,
        close_px=float(_p("close_px", 2.0)),
        settle_on_hit_range=(
            max(0.02, float(_p("settle_s", 0.065)) * 0.60),
            min(0.20, float(_p("settle_s", 0.065)) * 1.40),
        ),
    )

    return target


def random_mouse_movement(
    *,
    cfg: RandomMouseConfig = RandomMouseConfig(),
    controller: Optional[Controller] = None,
    bounds: Optional[Bounds] = None,
    executor: Optional[MouseExecutor] = None,
    speed_pct: float = 100.0,
    log_metrics: bool = False,
):
    if random.random() >= float(cfg.chance):
        return
    if bounds is None:
        bounds = get_default_bounds()

    ex = executor or PynputExecutor(controller)
    p = clamp_point(ex.get_pos(), bounds)
    nx = clamp_point(
        (
            p[0] + random.randint(cfg.min_px, cfg.max_px) * random.choice([-1, 1]),
            p[1] + random.randint(cfg.min_px, cfg.max_px) * random.choice([-1, 1]),
        ),
        bounds,
    )
    move_cursor(nx, controller=controller, bounds=bounds, executor=ex, speed_pct=speed_pct, log_metrics=log_metrics)
    time.sleep(random.uniform(cfg.min_s, cfg.max_s))


def move_and_click(
    pos: Point,
    *,
    button: MouseButton = "left",
    motion: CursorMotionConfig = CursorMotionConfig(),
    click_cfg: ClickConfig = ClickConfig(),
    controller: Optional[Controller] = None,
    bounds: Optional[Bounds] = None,
    rand_cfg: Optional[RandomMouseConfig] = None,
    rand_before: bool = True,
    settle: SettleConfig = SettleConfig(),
    press: PressConfig = PressConfig(),
    executor: Optional[MouseExecutor] = None,
    speed_pct: float = 100.0,
    overshoot_chance: float = 0.22,
    micro_pause_chance: float = 0.35,
    tremor_chance: float = 0.34,
    log_metrics: bool = False,
) -> Point:
    ex = executor or PynputExecutor(controller)
    if bounds is None:
        bounds = get_default_bounds()

    if click_cfg.button != button:
        click_cfg = ClickConfig(
            delay=click_cfg.delay,
            button=button,
            mode=click_cfg.mode,
            tap_min_s=click_cfg.tap_min_s,
            tap_max_s=click_cfg.tap_max_s,
            lock_pos=click_cfg.lock_pos,
        )

    if rand_cfg is not None and rand_before:
        random_mouse_movement(
            cfg=rand_cfg,
            controller=controller,
            bounds=bounds,
            executor=ex,
            speed_pct=speed_pct,
        )

    target = clamp_point((int(pos[0]), int(pos[1])), bounds)
    start = clamp_point(ex.get_pos(), bounds)
    dist = ((target[0] - start[0]) ** 2 + (target[1] - start[1]) ** 2) ** 0.5

    speed_mult, over_mult, _ = _energy_modifiers()
    overshoot_chance = float(overshoot_chance) * over_mult
    speed_pct = float(speed_pct) * speed_mult

    if dist < 8.0:
        move_cursor(
            target,
            config=CursorMotionConfig(duration=random.uniform(0.06, 0.14), fps=motion.fps),
            controller=controller,
            bounds=bounds,
            executor=ex,
            speed_pct=speed_pct,
            log_metrics=log_metrics,
        )

        base = float(_p("pre_click_s", 0.085))
        if random.random() < 0.82:
            time.sleep(random.uniform(max(0.015, base * 0.55), min(0.22, base * 1.60)))
        else:
            time.sleep(random.uniform(0.14, 0.42))

        time.sleep(random.uniform(0.015, 0.120))
        click(config=click_cfg, controller=controller, press=press, executor=ex)

        settle_delay = _sample_settle_delay(settle)
        if settle_delay > 0:
            time.sleep(settle_delay)

        if rand_cfg is not None and not rand_before:
            random_mouse_movement(
                cfg=rand_cfg,
                controller=controller,
                bounds=bounds,
                executor=ex,
                speed_pct=speed_pct,
                log_metrics=log_metrics,
            )
        return target

    wave = random.uniform(0.88, 1.12)
    speed_pct = float(speed_pct) * wave

    steps = plan_move(start, target, config=motion, bounds=bounds, speed_pct=speed_pct)
    _run_steps(
        ex,
        steps,
        target=target,
        settle_before=0.0,
        log_metrics=log_metrics,
        close_px=float(_p("close_px", 2.0)),
        settle_on_hit_range=(
            max(0.02, float(_p("settle_s", 0.065)) * 0.60),
            min(0.20, float(_p("settle_s", 0.065)) * 1.40),
        ),
    )

    base = float(_p("pre_click_s", 0.085))
    if random.random() < 0.82:
        time.sleep(random.uniform(max(0.015, base * 0.55), min(0.22, base * 1.60)))
    else:
        time.sleep(random.uniform(0.14, 0.42))

    click(config=click_cfg, controller=controller, press=press, executor=ex)

    settle_delay = _sample_settle_delay(settle)
    if settle_delay > 0:
        time.sleep(settle_delay)

    if rand_cfg is not None and not rand_before:
        random_mouse_movement(
            cfg=rand_cfg,
            controller=controller,
            bounds=bounds,
            executor=ex,
            speed_pct=speed_pct,
            log_metrics=log_metrics,
        )

    return target


def _get_primary_bounds() -> Bounds:
    user32 = ctypes.windll.user32
    w = int(user32.GetSystemMetrics(0))
    h = int(user32.GetSystemMetrics(1))
    return (0, 0, w - 1, h - 1)


def _rand_point_in(bounds: Bounds, margin: int = 80) -> Point:
    x0, y0, x1, y1 = bounds
    m = int(max(0, margin))
    return (
        random.randint(x0 + m, x1 - m),
        random.randint(y0 + m, y1 - m),
    )


def main_test():
    print("\n🧪 AI Cursor MAIN TEST\n")

    print(
        "Profile loaded:",
        "speed", _p("speed_min"), _p("speed_max"),
        "overshoot", _p("overshoot_min"), _p("overshoot_max"),
        "pre_click_s", _p("pre_click_s"),
        "click_hold_s", _p("click_hold_s"),
        "settle_s", _p("settle_s"),
        "close_px", _p("close_px"),
    )

    bounds = _get_primary_bounds()
    print("Bounds (primary):", bounds)

    n = int(os.getenv("AI_TEST_N", "25"))
    margin = int(os.getenv("AI_TEST_MARGIN", "90"))
    speed_pct = float(os.getenv("AI_TEST_SPEED_PCT", "100"))
    do_click = os.getenv("AI_TEST_CLICK", "0").strip().lower() in ("1", "true", "yes", "y")
    pause_min = float(os.getenv("AI_TEST_PAUSE_MIN", "0.20"))
    pause_max = float(os.getenv("AI_TEST_PAUSE_MAX", "0.65"))

    print(f"Config: n={n} margin={margin} speed_pct={speed_pct} click={do_click}")
    input("Druk Enter om te starten… (Ctrl+C om te stoppen)\n")

    for i in range(1, n + 1):
        p = _rand_point_in(bounds, margin=margin)
        print(f"➡️  {i}/{n} target={p}")

        t0 = time.time()
        if do_click:
            move_and_click(p, bounds=bounds, speed_pct=speed_pct)
        else:
            move_cursor(p, bounds=bounds, speed_pct=speed_pct)
        dt = (time.time() - t0) * 1000.0

        time.sleep(random.uniform(pause_min, pause_max))
        print(f"✅ done {dt:.1f} ms\n")

    print("🎉 Klaar.")


if __name__ == "__main__":
    main_test()