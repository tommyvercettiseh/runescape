from __future__ import annotations

import time
import random
from dataclasses import dataclass
from typing import Optional, Tuple, Literal, Protocol

from pynput.mouse import Controller, Button

# 👇 jouw planner (movement) zit hier:
from core.ai_cursor_movement import (
    plan_move,
    get_default_bounds,
    clamp_point,
    CursorMotionConfig,
)

MouseButton = Literal["left", "right"]
Point = Tuple[int, int]
Bounds = Tuple[int, int, int, int]

_DEFAULT_MOUSE = Controller()

# =========================
# MODELS (zelfde als jij had)
# =========================
@dataclass(frozen=True)
class ClickConfig:
    delay: float = 0.05
    button: MouseButton = "left"

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
    min_s: float = 0.06
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


# =========================
# EXECUTOR INTERFACE
# =========================
class MouseExecutor(Protocol):
    def get_pos(self) -> Point: ...
    def move_abs(self, x: int, y: int) -> None: ...
    def click(self, button: MouseButton) -> None: ...


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


# =========================
# HELPERS
# =========================
def _sleep_jitter(base: float, lo: float, hi: float) -> None:
    d = random.uniform(max(lo, base * 0.70), min(hi, base * 1.60))
    time.sleep(d)


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
) -> Point:
    ex = executor or PynputExecutor(controller)

    if bounds is None:
        bounds = get_default_bounds()

    target = clamp_point((int(pos[0]), int(pos[1])), bounds)
    start = clamp_point(ex.get_pos(), bounds)

    steps = plan_move(start, target, config=config, bounds=bounds)
    for st in steps:
        ex.move_abs(st.x, st.y)
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
        config = ClickConfig(delay=config.delay, button=button)

    _sleep_jitter(float(config.delay), lo=0.02, hi=0.22)

    # pynput: echte hold timing
    if isinstance(ex, PynputExecutor):
        btn = Button.right if config.button == "right" else Button.left
        ex.ctrl.press(btn)
        time.sleep(random.uniform(float(press.min_s), float(press.max_s)))
        ex.ctrl.release(btn)
        return

    # andere executors (Arduino etc): “1 click”
    ex.click(config.button)


def random_mouse_movement(
    *,
    cfg: RandomMouseConfig = RandomMouseConfig(),
    controller: Optional[Controller] = None,
    bounds: Optional[Bounds] = None,
    executor: Optional[MouseExecutor] = None,
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

        move_cursor((x2, y2), controller=controller, bounds=bounds, executor=ex)
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
) -> Point:
    ex = executor or PynputExecutor(controller)

    if bounds is None:
        bounds = get_default_bounds()

    if click_cfg.button != button:
        click_cfg = ClickConfig(delay=click_cfg.delay, button=button)

    if rand_cfg is not None and rand_before:
        random_mouse(cfg=rand_cfg, controller=controller, bounds=bounds, executor=ex)

    end_pos = move_cursor(pos, config=motion, controller=controller, bounds=bounds, executor=ex)

    if random.random() < float(settle.chance):
        if random.random() < float(settle.long_chance):
            time.sleep(random.uniform(float(settle.long_min_s), float(settle.long_max_s)))
        else:
            time.sleep(random.uniform(float(settle.min_s), float(settle.max_s)))

    click(config=click_cfg, controller=controller, press=press, executor=ex)

    if rand_cfg is not None and not rand_before:
        random_mouse(cfg=rand_cfg, controller=controller, bounds=bounds, executor=ex)

    return end_pos
