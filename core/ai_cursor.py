# === START BOOTSTRAP ===
# WAT: Module voor muisbewegingen + klikken (primitives).
# WAAROM: Input-gedrag centraal, herbruikbaar, multi-monitor safe.
# === END BOOTSTRAP ===

from __future__ import annotations
import time
import random
import math
import ctypes
from dataclasses import dataclass
from typing import Optional, Tuple, Literal

import pyautogui
from pynput.mouse import Controller, Button

ICON_ACTION = "▶"
ICON_OK = "✅"
ICON_WARN = "⚠️"
ICON_POS = "📍"
ICON_MOVE = "🧭"
ICON_RAND = "🎲"

MouseButton = Literal["left", "right"]
Point = Tuple[int, int]
Bounds = Tuple[int, int, int, int]  # (x1,y1,x2,y2) absolute coords

_DEFAULT_MOUSE = Controller()

# =========================
# TUNING
# =========================
SPEED_PERCENT = 70  # 100 = snel, 70 = rustig, 55 = traag/precies
USE_VIRTUAL_BOUNDS = True  # True = multi-monitor safe, False = alleen primary
MAX_DURATION_PER_MOVE = 1.65  # caps lange moves zodat het niet te traag wordt


# === START MODELS ===
@dataclass(frozen=True)
class CursorMotionConfig:
    duration: float = 0.35
    fps: int = 120
    min_duration: float = 0.08
    min_steps: int = 12


@dataclass(frozen=True)
class ClickConfig:
    # basis pre-click delay (wordt hieronder nog licht “menselijk” gejitterd)
    delay: float = 0.05
    button: MouseButton = "left"


@dataclass(frozen=True)
class SettleConfig:
    # pauze na aankomen op target vóór click
    chance: float = 0.90
    min_s: float = 0.06
    max_s: float = 0.18
    # soms wat langer “even kijken”
    long_chance: float = 0.08
    long_min_s: float = 0.22
    long_max_s: float = 0.55


@dataclass(frozen=True)
class PressConfig:
    # mouseDown hold voordat mouseUp komt
    min_s: float = 0.06
    max_s: float = 0.18


@dataclass(frozen=True)
class RandomMouseConfig:
    chance: float = 0.06
    max_moves: int = 2
    min_radius: int = 6
    max_radius: int = 80
    min_duration: float = 0.06
    max_duration: float = 0.22
    pause_min: float = 0.02
    pause_max: float = 0.12
    verbose: bool = False
# === END MODELS ===


# === START HELPERS ===
def _ease_in_out_quad(t: float) -> float:
    return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _clamp_duration(duration: float, min_duration: float) -> float:
    return max(float(min_duration), float(duration))


def _compute_steps(duration: float, fps: int, min_steps: int) -> int:
    fps = max(1, int(fps))
    return max(int(min_steps), int(duration * fps))


def _log(msg: str) -> None:
    print(msg)


def _speed_scale() -> float:
    return _clamp(SPEED_PERCENT / 100.0, 0.25, 1.25)


def get_virtual_screen_bounds() -> Bounds:
    user32 = ctypes.windll.user32
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    x1 = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    y1 = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    w = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    h = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
    return (x1, y1, x1 + w, y1 + h)


def get_primary_bounds() -> Bounds:
    w, h = pyautogui.size()
    return (0, 0, int(w), int(h))


def get_default_bounds() -> Bounds:
    return get_virtual_screen_bounds() if USE_VIRTUAL_BOUNDS else get_primary_bounds()


def clamp_point(p: Point, bounds: Bounds) -> Point:
    x, y = int(p[0]), int(p[1])
    x1, y1, x2, y2 = bounds
    x = max(x1, min(x, x2 - 1))
    y = max(y1, min(y, y2 - 1))
    return (x, y)


def _bezier2(p0: Point, p1: Tuple[float, float], p2: Point, t: float) -> Tuple[float, float]:
    inv = 1.0 - t
    x = inv * inv * p0[0] + 2 * inv * t * p1[0] + t * t * p2[0]
    y = inv * inv * p0[1] + 2 * inv * t * p1[1] + t * t * p2[1]
    return x, y


def _sleep_jitter(base: float, lo: float, hi: float) -> None:
    # kleine variatie zodat delays niet “blokkerig” zijn
    d = random.uniform(max(lo, base * 0.70), min(hi, base * 1.60))
    time.sleep(d)
# === END HELPERS ===


# === START CORE LOGIC ===
def move_cursor(
    pos: Point,
    *,
    config: CursorMotionConfig = CursorMotionConfig(),
    controller: Optional[Controller] = None,
    bounds: Optional[Bounds] = None,
) -> Point:
    """
    Vloeiende move naar pos.
    Geen teleport op het einde (cap safe).
    """
    ctrl = controller or _DEFAULT_MOUSE
    scale = _speed_scale()

    if bounds is None:
        bounds = get_default_bounds()

    x2, y2 = clamp_point((int(pos[0]), int(pos[1])), bounds)
    x1, y1 = clamp_point((int(ctrl.position[0]), int(ctrl.position[1])), bounds)

    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)

    if dist <= 1.0:
        ctrl.position = (x2, y2)
        return (x2, y2)

    speed = random.uniform(1200, 2000) * scale
    base = dist / max(240.0, speed)
    base = _clamp(base, float(config.min_duration), float(config.duration))

    duration = _clamp_duration(base * random.uniform(0.96, 1.06), config.min_duration)
    duration = duration / scale
    duration = _clamp(duration, float(config.min_duration), float(MAX_DURATION_PER_MOVE))

    fps = int(_clamp(int(config.fps * random.uniform(0.96, 1.04)), 65, 170))
    fps = int(_clamp(fps * (0.92 + 0.16 * scale), 55, 180))

    steps = _compute_steps(duration, fps, config.min_steps)

    if dist < 90:
        cx = x1 + dx * 0.5
        cy = y1 + dy * 0.5
    else:
        nxp = -dy / dist
        nyp = dx / dist
        bend = random.uniform(-1.0, 1.0) * min(85.0, dist * 0.14)
        cx = x1 + dx * random.uniform(0.38, 0.62) + nxp * bend
        cy = y1 + dy * random.uniform(0.38, 0.62) + nyp * bend

    p0 = (x1, y1)
    p1 = (cx, cy)
    p2 = (x2, y2)

    amp = _clamp(dist * 0.0024, 0.15, 2.0) * random.uniform(0.85, 1.10)
    phase = random.uniform(0.0, math.tau)
    freq = random.uniform(0.9, 1.4)

    nx = -dy / dist
    ny = dx / dist

    max_step_px = int(_clamp(34 * scale, 8, 42))

    min_steps_for_cap = int(math.ceil(dist / max_step_px))
    steps = max(steps, min_steps_for_cap)
    dt = duration / steps if steps > 0 else 0.0

    for i in range(1, steps + 1):
        t = i / steps
        s = _ease_in_out_quad(t)

        x, y = _bezier2(p0, p1, p2, s)

        decay = 1.0 - s
        drift = math.sin(phase + s * math.tau * freq) * amp * decay
        x += nx * drift
        y += ny * drift

        xi, yi = clamp_point((int(x), int(y)), bounds)

        curx, cury = clamp_point((int(ctrl.position[0]), int(ctrl.position[1])), bounds)
        ddx = xi - curx
        ddy = yi - cury
        step = math.hypot(ddx, ddy)
        if step > max_step_px:
            k = max_step_px / step
            xi = int(curx + ddx * k)
            yi = int(cury + ddy * k)
            xi, yi = clamp_point((xi, yi), bounds)

        ctrl.position = (xi, yi)
        time.sleep(_clamp(dt + random.uniform(-0.0010, 0.0010), 0.0006, 0.02))

    curx, cury = clamp_point((int(ctrl.position[0]), int(ctrl.position[1])), bounds)
    while (curx, cury) != (x2, y2):
        ddx = x2 - curx
        ddy = y2 - cury
        step = math.hypot(ddx, ddy)
        if step <= 0.9:
            break
        k = min(1.0, max_step_px / step)
        curx = int(curx + ddx * k)
        cury = int(cury + ddy * k)
        curx, cury = clamp_point((curx, cury), bounds)
        ctrl.position = (curx, cury)
        time.sleep(0.003)

    ctrl.position = (x2, y2)
    return (x2, y2)


def click(
    *,
    button: MouseButton | None = None,
    config: ClickConfig = ClickConfig(),
    controller: Optional[Controller] = None,
    press: PressConfig = PressConfig(),
) -> None:
    ctrl = controller or _DEFAULT_MOUSE

    # als button is meegegeven, override config.button
    if button is not None and config.button != button:
        config = ClickConfig(delay=config.delay, button=button)

    # pre-click delay (met beetje variatie)
    _sleep_jitter(float(config.delay), lo=0.02, hi=0.22)

    btn = Button.right if config.button == "right" else Button.left

    # press -> hold -> release
    ctrl.press(btn)
    time.sleep(random.uniform(float(press.min_s), float(press.max_s)))
    ctrl.release(btn)

# === END CORE LOGIC ===


# === START RANDOM MOUSE ===
def random_mouse(
    *,
    cfg: RandomMouseConfig = RandomMouseConfig(),
    controller: Optional[Controller] = None,
    bounds: Optional[Bounds] = None,
) -> bool:
    if cfg.chance <= 0:
        return False
    if random.random() > float(cfg.chance):
        return False

    ctrl = controller or _DEFAULT_MOUSE
    if bounds is None:
        bounds = get_default_bounds()

    scale = _speed_scale()
    moves = random.randint(1, max(1, int(cfg.max_moves)))

    if cfg.verbose:
        _log(f"{ICON_RAND} random_mouse ✅ moves={moves}")

    for _ in range(moves):
        x1, y1 = clamp_point((int(ctrl.position[0]), int(ctrl.position[1])), bounds)

        radius_lo = int(max(3, cfg.min_radius * scale))
        radius_hi = int(max(radius_lo + 1, cfg.max_radius * scale))
        radius = random.randint(radius_lo, radius_hi)

        dx = int(radius * random.uniform(0.55, 1.0) * (1 if random.random() < 0.5 else -1))
        dy = int(radius * random.uniform(0.55, 1.0) * (1 if random.random() < 0.5 else -1))

        x2, y2 = clamp_point((x1 + dx, y1 + dy), bounds)

        dur = random.uniform(float(cfg.min_duration), float(cfg.max_duration)) / max(0.6, scale)
        fps = random.randint(85, 150)

        motion = CursorMotionConfig(
            duration=min(dur, 0.40),
            fps=fps,
            min_duration=min(0.10, dur),
            min_steps=10,
        )

        move_cursor((x2, y2), config=motion, controller=ctrl, bounds=bounds)
        time.sleep(random.uniform(float(cfg.pause_min), float(cfg.pause_max)))

    return True
# === END RANDOM MOUSE ===


# === START API ===
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
) -> Point:
    ctrl = controller or _DEFAULT_MOUSE
    if bounds is None:
        bounds = get_default_bounds()

    # left/right centraal
    if click_cfg.button != button:
        click_cfg = ClickConfig(delay=click_cfg.delay, button=button)

    if rand_cfg is not None and rand_before:
        random_mouse(cfg=rand_cfg, controller=ctrl, bounds=bounds)

    end_pos = move_cursor(pos, config=motion, controller=ctrl, bounds=bounds)

    # ✅ settle na aankomst (meestal kort, soms wat langer)
    if random.random() < float(settle.chance):
        if random.random() < float(settle.long_chance):
            time.sleep(random.uniform(float(settle.long_min_s), float(settle.long_max_s)))
        else:
            time.sleep(random.uniform(float(settle.min_s), float(settle.max_s)))

    click(config=click_cfg, controller=ctrl, press=press)

    if rand_cfg is not None and not rand_before:
        random_mouse(cfg=rand_cfg, controller=ctrl, bounds=bounds)

    return end_pos
# === END API ===


# === START CLI TEST ===
if __name__ == "__main__":
    _log(f"\n🧪 ai_cursor SELF TEST\n{ICON_WARN} Niet bewegen met je muis 🙂\n")
    time.sleep(2)

    bounds = get_default_bounds()
    x1, y1, x2, y2 = bounds
    _log(f"{ICON_ACTION} Bounds: {bounds}")
    _log(f"{ICON_ACTION} SPEED_PERCENT: {SPEED_PERCENT}% | virtual={USE_VIRTUAL_BOUNDS} | maxdur={MAX_DURATION_PER_MOVE}s")

    motion = CursorMotionConfig(duration=0.55, fps=150, min_duration=0.10, min_steps=16)

    for i in range(6):
        p = (random.randint(x1 + 120, x2 - 120), random.randint(y1 + 120, y2 - 120))
        _log(f"{ICON_MOVE} Move {i+1}/6 → {ICON_POS} {p}")
        move_and_click(p, motion=motion, button="left")
        time.sleep(0.20)

    _log(f"\n{ICON_OK} klaar\n")
# === END CLI TEST ===
