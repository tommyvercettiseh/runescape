from __future__ import annotations

import time
import random
from dataclasses import dataclass
from typing import Optional, Tuple, Literal, Protocol

from pynput.mouse import Controller, Button

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

# =========================
# MODELS
# =========================
@dataclass(frozen=True)
class ClickConfig:
    delay: float = 0.05
    button: MouseButton = "left"

    # Backwards compatible
    mode: ClickMode = "hold"          # "hold" (oud), "tap", "safe_tap"
    tap_min_s: float = 0.012          # alleen bij tap/safe_tap
    tap_max_s: float = 0.028          # alleen bij tap/safe_tap
    lock_pos: bool = False            # bij safe_tap: cursor lock vóór release


@dataclass(frozen=True)
class SettleConfig:
    chance: float = 0.90
    min_s: float = 0.06
    max_s: float = 0.18
    long_chance: float = 0.08
    long_min_s: float = 0.22
    long_max_s: float = 0.55


@dataclass(frozen=True)
class PressConfig:
    min_s: float = 0.04
    max_s: float = 0.18


@dataclass(frozen=True)
class RandomMouseConfig:
    chance: float = 0.06
    max_moves: int = 2
    min_radius: int = 6
    max_radius: int = 80
    pause_min: float = 0.02
    pause_max: float = 0.12
    verbose: bool = False


@dataclass(frozen=True)
class ScrollConfig:
    min_steps: int = 3
    max_steps: int = 9
    step_min: int = 80
    step_max: int = 180
    delay_min: float = 0.015
    delay_max: float = 0.045

    # extra “human” micro scrolls
    jitter_chance: float = 0.12
    jitter_min: int = 12
    jitter_max: int = 45


# =========================
# EXECUTOR INTERFACE
# =========================
class MouseExecutor(Protocol):
    def get_pos(self) -> Point: ...
    def move_abs(self, x: int, y: int) -> None: ...
    def click(self, button: MouseButton) -> None: ...
    def scroll(self, dx: int, dy: int) -> None: ...


class PynputExecutor:
    def __init__(self, controller: Optional[Controller] = None):
        self.ctrl = controller or _DEFAULT_MOUSE

    def get_pos(self) -> Point:
        x, y = self.ctrl.position
        return int(x), int(y)

    def move_abs(self, x: int, y: int) -> None:
        self.ctrl.position = (int(x), int(y))

    def click(self, button: MouseButton) -> None:
        btn = Button.right if button == "right" else Button.left
        self.ctrl.press(btn)
        self.ctrl.release(btn)

    def scroll(self, dx: int, dy: int) -> None:
        self.ctrl.scroll(int(dx), int(dy))


# =========================
# HELPERS
# =========================
def _sleep_jitter(base: float, lo: float, hi: float) -> None:
    d = random.uniform(max(lo, base * 0.70), min(hi, base * 1.60))
    time.sleep(d)


def _btn(button: MouseButton):
    return Button.right if button == "right" else Button.left


def _swap_if_needed(a: int, b: int) -> tuple[int, int]:
    a = int(a)
    b = int(b)
    return (a, b) if b >= a else (b, a)


def _speed_factor(speed_pct: float) -> float:
    try:
        sp = float(speed_pct)
    except Exception:
        sp = 100.0

    if sp <= 0:
        sp = 1.0

    # sneller = minder delay
    return 100.0 / sp


def _overshoot_target(start: Point, target: Point, bounds: Bounds, *, chance=0.22, min_px=6, max_px=22) -> Point | None:
    if random.random() > float(chance):
        return None

    x1, y1 = start
    x2, y2 = target
    dx = x2 - x1
    dy = y2 - y1
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 20:
        return None

    k = random.uniform(float(min_px), float(max_px)) / max(1.0, dist)
    ox = x2 + dx * k
    oy = y2 + dy * k

    # lateral deviation so overshoot isn't perfectly linear
    nx = -dy / dist
    ny = dx / dist
    lat = random.uniform(2.0, 10.0)
    if dist > 600:
        lat *= 1.2

    if random.random() < (0.55 + 0.2 * abs(_HAND_BIAS)):
        sign = 1 if _HAND_BIAS >= 0 else -1
    else:
        sign = 1 if random.random() < 0.5 else -1

    ox += nx * lat * sign
    oy += ny * lat * sign

    ox = int(round(ox))
    oy = int(round(oy))
    return clamp_point((ox, oy), bounds)


def _undershoot_target(start: Point, target: Point, bounds: Bounds, *, chance=0.18, min_px=6, max_px=18) -> Point | None:
    if random.random() > float(chance):
        return None

    x1, y1 = start
    x2, y2 = target
    dx = x2 - x1
    dy = y2 - y1
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 20:
        return None

    k = random.uniform(float(min_px), float(max_px)) / max(1.0, dist)
    ux = int(round(x2 - dx * k))
    uy = int(round(y2 - dy * k))
    return clamp_point((ux, uy), bounds)


def _micro_nudge(pos: Point, bounds: Bounds, *, min_px=1, max_px=3) -> Point:
    dx = random.randint(int(min_px), int(max_px)) * (1 if random.random() < 0.5 else -1)
    dy = random.randint(int(min_px), int(max_px)) * (1 if random.random() < 0.5 else -1)
    return clamp_point((pos[0] + dx, pos[1] + dy), bounds)


def _bend_point(start: Point, target: Point, bounds: Bounds, *, min_px=6, max_px=30) -> Point:
    x1, y1 = start
    x2, y2 = target
    dx = x2 - x1
    dy = y2 - y1
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 1.0:
        return target

    nx = -dy / dist
    ny = dx / dist
    offset = random.uniform(float(min_px), float(max_px))

    # slight directional bias per session
    if random.random() < (0.55 + 0.2 * abs(_HAND_BIAS)):
        sign = 1 if _HAND_BIAS >= 0 else -1
    else:
        sign = 1 if random.random() < 0.5 else -1

    mid_t = random.uniform(0.35, 0.65)
    mx = x1 + dx * mid_t + nx * offset * sign
    my = y1 + dy * mid_t + ny * offset * sign
    return clamp_point((int(mx), int(my)), bounds)


def _choose_tail_mode(
    *,
    micro_pause_chance: float,
    pre_click_chance: float,
    tremor_chance: float,
    final_settle: bool,
) -> str:
    # keep most clicks clean; allow at most one micro behavior
    none_w = 0.60
    slow_w = float(micro_pause_chance) * 0.18 + (0.18 if final_settle else 0.0)
    drift_w = float(pre_click_chance) * 0.22
    wiggle_w = float(tremor_chance) * 0.18
    total = none_w + slow_w + drift_w + wiggle_w

    r = random.random() * total
    if r < none_w:
        return "none"
    r -= none_w
    if r < slow_w:
        return "slow"
    if r < slow_w + drift_w:
        return "drift"
    return "wiggle"


def _apply_tail_variation(
    steps: list[PlannedStep],
    target: Point,
    bounds: Bounds,
    *,
    mode: str,
) -> list[PlannedStep]:
    if not steps or mode == "none":
        # ensure last step ends on target
        if steps:
            last = steps[-1]
            steps[-1] = PlannedStep(x=target[0], y=target[1], sleep_s=last.sleep_s)
        return steps

    tail_len = min(len(steps) - 1, random.randint(4, 10))
    if tail_len < 2:
        last = steps[-1]
        steps[-1] = PlannedStep(x=target[0], y=target[1], sleep_s=last.sleep_s)
        return steps

    base_amp = random.uniform(1.0, 3.0)
    new_steps: list[PlannedStep] = []
    start_i = len(steps) - tail_len

    for i, st in enumerate(steps):
        x, y, s = st.x, st.y, st.sleep_s
        if start_i <= i < len(steps) - 1:
            frac = (i - start_i) / max(1, tail_len - 1)
            decay = (1.0 - frac) ** 1.2
            amp = base_amp * decay

            if mode == "drift":
                dx = random.uniform(-amp, amp)
                dy = random.uniform(-amp, amp)
            elif mode == "wiggle":
                sign = -1 if (i % 2 == 0) else 1
                dx = sign * random.uniform(0.0, amp)
                dy = -sign * random.uniform(0.0, amp)
            else:
                dx = 0.0
                dy = 0.0

            x, y = clamp_point((int(round(x + dx)), int(round(y + dy))), bounds)

        new_steps.append(PlannedStep(x=x, y=y, sleep_s=s))

    # force exact end at target
    last = new_steps[-1]
    new_steps[-1] = PlannedStep(x=target[0], y=target[1], sleep_s=last.sleep_s)
    return new_steps


def _compress_steps(steps: list[PlannedStep]) -> list[PlannedStep]:
    if not steps:
        return steps
    out: list[PlannedStep] = []
    for st in steps:
        if out and (out[-1].x, out[-1].y) == (st.x, st.y):
            prev = out[-1]
            out[-1] = PlannedStep(x=prev.x, y=prev.y, sleep_s=prev.sleep_s + st.sleep_s)
        else:
            out.append(st)
    return out


# =========================
# CORE
# =========================
def move_cursor(
    pos: Point,
    *,
    config: CursorMotionConfig = CursorMotionConfig(),
    controller: Optional[Controller] = None,
    bounds: Optional[Bounds] = None,
    executor: Optional[MouseExecutor] = None,
    speed_pct: float = 100.0,
) -> Point:
    ex = executor or PynputExecutor(controller)

    if bounds is None:
        bounds = get_default_bounds()

    target = clamp_point((int(pos[0]), int(pos[1])), bounds)
    start = clamp_point(ex.get_pos(), bounds)
    dist = ((target[0] - start[0]) ** 2 + (target[1] - start[1]) ** 2) ** 0.5

    # micro moves: direct, no planner feel
    if dist < 8.0:
        ex.move_abs(target[0], target[1])
        if random.random() < 0.70:
            time.sleep(random.uniform(0.003, 0.012))
        return target

    steps = []
    # occasional bend to avoid overly straight paths
    if dist > 140 and random.random() < 0.28:
        mid = _bend_point(start, target, bounds, min_px=8, max_px=42)
        steps.extend(plan_move(start, mid, config=config, bounds=bounds, speed_pct=speed_pct))
        steps.extend(plan_move(mid, target, config=config, bounds=bounds, speed_pct=speed_pct))
    else:
        steps = plan_move(start, target, config=config, bounds=bounds, speed_pct=speed_pct)

    last_xy = start
    for st in steps:
        xy = (st.x, st.y)
        if xy != last_xy:
            ex.move_abs(st.x, st.y)
            last_xy = xy
        if st.sleep_s:
            time.sleep(st.sleep_s)

    return target


def click(
    *,
    button: MouseButton | None = None,
    config: ClickConfig = ClickConfig(),
    controller: Optional[Controller] = None,
    press: PressConfig = PressConfig(),
    executor: Optional[MouseExecutor] = None,
) -> None:
    ex = executor or PynputExecutor(controller)

    if button is not None and config.button != button:
        config = ClickConfig(
            delay=config.delay,
            button=button,
            mode=config.mode,
            tap_min_s=config.tap_min_s,
            tap_max_s=config.tap_max_s,
            lock_pos=config.lock_pos,
        )

    _sleep_jitter(float(config.delay), lo=0.02, hi=0.22)

    # Alleen pynput kan echte down/up + timing
    if isinstance(ex, PynputExecutor):
        btn = _btn(config.button)

        # Tap modes: korter vasthouden, minder drag
        if config.mode in ("tap", "safe_tap"):
            hold_s = random.uniform(float(config.tap_min_s), float(config.tap_max_s))
            x0, y0 = ex.ctrl.position

            ex.ctrl.press(btn)
            time.sleep(hold_s)

            if config.mode == "safe_tap" or config.lock_pos:
                ex.ctrl.position = (int(x0), int(y0))
                time.sleep(0.001)

            ex.ctrl.release(btn)
            return

        # Hold mode: oud gedrag
        ex.ctrl.press(btn)
        hold = random.uniform(float(press.min_s), float(press.max_s))
        if random.random() < 0.18:
            hold *= random.uniform(1.15, 1.85)
        time.sleep(hold)
        ex.ctrl.release(btn)
        return

    # Andere executors (Arduino etc)
    ex.click(config.button)


def scroll(
    *,
    direction: ScrollDir,
    cfg: ScrollConfig = ScrollConfig(),
    controller: Optional[Controller] = None,
    executor: Optional[MouseExecutor] = None,
    speed_pct: float = 100.0,
    verbose: bool = False,
) -> int:
    """
    Echte scroll (pynput).
    direction: "up" of "down"
    Returns: signed total scroll units.
    """
    if direction not in ("up", "down"):
        raise ValueError("direction moet 'up' of 'down' zijn")

    ex = executor or PynputExecutor(controller)

    min_steps, max_steps = _swap_if_needed(cfg.min_steps, cfg.max_steps)
    step_min, step_max = _swap_if_needed(cfg.step_min, cfg.step_max)

    steps = random.randint(min_steps, max_steps)
    sign = 1 if direction == "up" else -1

    factor = _speed_factor(speed_pct)
    total = 0

    if verbose:
        print(f"🌀 scroll {direction} | steps={steps} | step={step_min}..{step_max} | speed={float(speed_pct):.0f}%")

    for _ in range(steps):
        amt = random.randint(step_min, step_max)
        ex.scroll(0, sign * amt)
        total += sign * amt

        if cfg.jitter_chance > 0 and random.random() < float(cfg.jitter_chance):
            j = random.randint(int(cfg.jitter_min), int(cfg.jitter_max))
            ex.scroll(0, sign * j)
            total += sign * j

        d = random.uniform(float(cfg.delay_min), float(cfg.delay_max)) * factor
        time.sleep(max(0.0, d))

    return total


def random_mouse_movement(
    *,
    cfg: RandomMouseConfig = RandomMouseConfig(),
    controller: Optional[Controller] = None,
    bounds: Optional[Bounds] = None,
    executor: Optional[MouseExecutor] = None,
    speed_pct: float = 100.0,
) -> bool:
    if cfg.chance <= 0:
        return False
    if random.random() > float(cfg.chance):
        return False

    ex = executor or PynputExecutor(controller)

    if bounds is None:
        bounds = get_default_bounds()

    moves = random.randint(1, max(1, int(cfg.max_moves)))
    for _ in range(moves):
        x1, y1 = clamp_point(ex.get_pos(), bounds)
        radius = random.randint(int(cfg.min_radius), int(cfg.max_radius))

        dx = int(radius * random.uniform(0.55, 1.0) * (1 if random.random() < 0.5 else -1))
        dy = int(radius * random.uniform(0.55, 1.0) * (1 if random.random() < 0.5 else -1))
        x2, y2 = clamp_point((x1 + dx, y1 + dy), bounds)

        move_cursor(
            (x2, y2),
            controller=controller,
            bounds=bounds,
            executor=ex,
            speed_pct=speed_pct,
        )
        time.sleep(random.uniform(float(cfg.pause_min), float(cfg.pause_max)))

    return True


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
    # humanize
    overshoot_chance: float = 0.22,
    micro_pause_chance: float = 0.35,
    tremor_chance: float = 0.35,
    tremor_px_min: int = 1,
    tremor_px_max: int = 4,
    final_settle: bool = True,
    # extra humanize
    undershoot_chance: float = 0.18,
    pre_click_chance: float = 0.42,
    pre_click_px_min: int = 1,
    pre_click_px_max: int = 4,
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

    # very small move: direct, no extra behavior
    if dist < 8.0:
        ex.move_abs(target[0], target[1])
        if random.random() < 0.65:
            time.sleep(random.uniform(0.003, 0.012))
        click(config=click_cfg, controller=controller, press=press, executor=ex)
        if rand_cfg is not None and not rand_before:
            random_mouse_movement(
                cfg=rand_cfg,
                controller=controller,
                bounds=bounds,
                executor=ex,
                speed_pct=speed_pct,
            )
        return target

    # subtle speed wave per move (human rhythm)
    wave = random.uniform(0.88, 1.12)
    speed_pct = float(speed_pct) * wave

    # build single continuous movement path
    through = None
    if dist > 20 and random.random() < float(overshoot_chance):
        through = _overshoot_target(start, target, bounds, chance=1.0)
    elif dist > 20 and random.random() < float(undershoot_chance):
        through = _undershoot_target(start, target, bounds, chance=1.0)
    elif dist > 140 and random.random() < 0.28:
        through = _bend_point(start, target, bounds, min_px=8, max_px=42)

    if through:
        steps = plan_move(start, through, config=motion, bounds=bounds, speed_pct=speed_pct)
        steps += plan_move(through, target, config=motion, bounds=bounds, speed_pct=speed_pct)
    else:
        steps = plan_move(start, target, config=motion, bounds=bounds, speed_pct=speed_pct)

    tail_mode = _choose_tail_mode(
        micro_pause_chance=micro_pause_chance,
        pre_click_chance=pre_click_chance,
        tremor_chance=tremor_chance,
        final_settle=final_settle,
    )
    steps = _apply_tail_variation(steps, target, bounds, mode=tail_mode)

    last_xy = start
    for st in steps:
        xy = (st.x, st.y)
        if xy != last_xy:
            ex.move_abs(st.x, st.y)
            last_xy = xy
        if st.sleep_s:
            time.sleep(st.sleep_s)

    end_pos = target

    click(config=click_cfg, controller=controller, press=press, executor=ex)

    if rand_cfg is not None and not rand_before:
        random_mouse_movement(
            cfg=rand_cfg,
            controller=controller,
            bounds=bounds,
            executor=ex,
            speed_pct=speed_pct,
        )

    return end_pos
