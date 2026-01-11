# === START BOOTSTRAP ===
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
Bounds = Tuple[int, int, int, int]

_DEFAULT_MOUSE = Controller()

# ============================================================
# ✅ TWEAK ZONE (easy edits later)
# ============================================================
USE_VIRTUAL_BOUNDS = True
MAX_DURATION_PER_MOVE = 1.65

# Tick-ritme (dit bepaalt vooral “smoothness”)
TICK_MIN = 0.006
TICK_MAX = 0.011

# Snelheid op basis van afstand (px/s). Smooth curve.
SPEED_MIN_PX_S = 700
SPEED_MAX_PX_S = 1500
SPEED_JITTER = 0.10            # kleine variatie per move

# Extra: soms bewust iets trager/medium
SLOW_CHANCE = 0.30
SLOW_MULT = 0.80               # 0.75–0.90 is prima

# Anti-schiet cap (max pixels per tick)
MAX_STEP_PX = 26

# Curve (minder = strakker)
BEND_MAX = 55.0
BEND_FACTOR = 0.10

# Drift (heel subtiel, anders “wiebel”)
DRIFT_SCALE = 0.0012
DRIFT_MIN = 0.08
DRIFT_MAX = 0.95
DRIFT_FREQ_MIN = 0.95
DRIFT_FREQ_MAX = 1.25

VERBOSE_MOVES = False
# ============================================================


# === MODELS ===
@dataclass(frozen=True)
class CursorMotionConfig:
    duration: float = 0.35
    fps: int = 120
    min_duration: float = 0.08
    min_steps: int = 12


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
    min_duration: float = 0.06
    max_duration: float = 0.22
    pause_min: float = 0.02
    pause_max: float = 0.12
    verbose: bool = False


# === HELPERS ===
def _ease_in_out_quad(t: float) -> float:
    return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _log(msg: str) -> None:
    print(msg)


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
    d = random.uniform(max(lo, base * 0.70), min(hi, base * 1.60))
    time.sleep(d)


def _pick_tick() -> float:
    return random.uniform(TICK_MIN, TICK_MAX)


def _speed_for_dist(dist: float) -> float:
    # smooth curve: korte moves niet te traag, lange moves niet overdreven snel
    # normaliseer dist (0..1-ish)
    k = 1.0 - math.exp(-dist / 550.0)
    speed = SPEED_MIN_PX_S + (SPEED_MAX_PX_S - SPEED_MIN_PX_S) * k
    speed *= random.uniform(1.0 - SPEED_JITTER, 1.0 + SPEED_JITTER)
    if random.random() < SLOW_CHANCE:
        speed *= SLOW_MULT
    return max(250.0, speed)


# === CORE LOGIC ===
def move_cursor(
    pos: Point,
    *,
    config: CursorMotionConfig = CursorMotionConfig(),
    controller: Optional[Controller] = None,
    bounds: Optional[Bounds] = None,
) -> Point:
    """
    Super vloeiende move:
    1) duration op afstand/speed
    2) vaste tick-rate (met mini jitter)
    3) bezier curve + subtiele drift
    4) max step cap zodat hij nooit 'schiet'
    """
    ctrl = controller or _DEFAULT_MOUSE
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

    speed = _speed_for_dist(dist)
    duration = dist / speed
    duration = _clamp(duration, float(config.min_duration), float(MAX_DURATION_PER_MOVE))

    tick = _pick_tick()
    steps = max(int(duration / tick), int(config.min_steps))

    # cap steps zodat het niet te lang wordt
    steps = min(steps, int(MAX_DURATION_PER_MOVE / TICK_MIN))

    # cap stapgrootte: genoeg steps om nooit grote jumps te maken
    min_steps_for_cap = int(math.ceil(dist / MAX_STEP_PX))
    steps = max(steps, min_steps_for_cap)

    if VERBOSE_MOVES:
        _log(f"{ICON_MOVE} dist={dist:.0f}px speed={speed:.0f}px/s dur={duration:.2f}s steps={steps}")

    # curve control point (rustig, niet te gek)
    if dist < 90:
        cx = x1 + dx * 0.5
        cy = y1 + dy * 0.5
    else:
        nxp = -dy / dist
        nyp = dx / dist
        bend = random.uniform(-1.0, 1.0) * min(BEND_MAX, dist * BEND_FACTOR)
        cx = x1 + dx * random.uniform(0.42, 0.58) + nxp * bend
        cy = y1 + dy * random.uniform(0.42, 0.58) + nyp * bend

    p0 = (x1, y1)
    p1 = (cx, cy)
    p2 = (x2, y2)

    # drift normal
    nx = -dy / dist
    ny = dx / dist
    amp = _clamp(dist * DRIFT_SCALE, DRIFT_MIN, DRIFT_MAX) * random.uniform(0.85, 1.10)
    phase = random.uniform(0.0, math.tau)
    freq = random.uniform(DRIFT_FREQ_MIN, DRIFT_FREQ_MAX)

    fx, fy = float(x1), float(y1)

    for i in range(1, steps + 1):
        t = i / steps
        s = _ease_in_out_quad(t)

        tx, ty = _bezier2(p0, p1, p2, s)

        decay = 1.0 - s
        drift = math.sin(phase + s * math.tau * freq) * amp * decay
        tx += nx * drift
        ty += ny * drift

        # cap stap naar target punt
        dx2 = tx - fx
        dy2 = ty - fy
        step_len = math.hypot(dx2, dy2)

        if step_len > MAX_STEP_PX and step_len > 0.0001:
            k = MAX_STEP_PX / step_len
            fx += dx2 * k
            fy += dy2 * k
        else:
            fx, fy = tx, ty

        xi, yi = clamp_point((int(round(fx)), int(round(fy))), bounds)
        ctrl.position = (xi, yi)

        time.sleep(_clamp(_pick_tick(), 0.002, 0.02))

    # micro-correct (geen snap)
    curx, cury = clamp_point((int(ctrl.position[0]), int(ctrl.position[1])), bounds)
    for _ in range(10):
        ddx = x2 - curx
        ddy = y2 - cury
        r = math.hypot(ddx, ddy)
        if r <= 1.3:
            break
        k = min(1.0, MAX_STEP_PX / max(1.0, r))
        curx = int(curx + ddx * k)
        cury = int(cury + ddy * k)
        curx, cury = clamp_point((curx, cury), bounds)
        ctrl.position = (curx, cury)
        time.sleep(_clamp(_pick_tick(), 0.002, 0.02))

    return clamp_point((int(ctrl.position[0]), int(ctrl.position[1])), bounds)


def click(
    *,
    button: MouseButton | None = None,
    config: ClickConfig = ClickConfig(),
    controller: Optional[Controller] = None,
    press: PressConfig = PressConfig(),
) -> None:
    ctrl = controller or _DEFAULT_MOUSE
    if button is not None and config.button != button:
        config = ClickConfig(delay=config.delay, button=button)

    _sleep_jitter(float(config.delay), lo=0.02, hi=0.22)

    btn = Button.right if config.button == "right" else Button.left
    ctrl.press(btn)
    time.sleep(random.uniform(float(press.min_s), float(press.max_s)))
    ctrl.release(btn)


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

    moves = random.randint(1, max(1, int(cfg.max_moves)))
    if cfg.verbose:
        _log(f"{ICON_RAND} random_mouse ✅ moves={moves}")

    for _ in range(moves):
        x1, y1 = clamp_point((int(ctrl.position[0]), int(ctrl.position[1])), bounds)
        radius = random.randint(int(cfg.min_radius), int(cfg.max_radius))

        dx = int(radius * random.uniform(0.55, 1.0) * (1 if random.random() < 0.5 else -1))
        dy = int(radius * random.uniform(0.55, 1.0) * (1 if random.random() < 0.5 else -1))
        x2, y2 = clamp_point((x1 + dx, y1 + dy), bounds)

        move_cursor((x2, y2), controller=ctrl, bounds=bounds)
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
) -> Point:
    ctrl = controller or _DEFAULT_MOUSE
    if bounds is None:
        bounds = get_default_bounds()

    if click_cfg.button != button:
        click_cfg = ClickConfig(delay=click_cfg.delay, button=button)

    if rand_cfg is not None and rand_before:
        random_mouse(cfg=rand_cfg, controller=ctrl, bounds=bounds)

    end_pos = move_cursor(pos, config=motion, controller=ctrl, bounds=bounds)

    if random.random() < float(settle.chance):
        if random.random() < float(settle.long_chance):
            time.sleep(random.uniform(float(settle.long_min_s), float(settle.long_max_s)))
        else:
            time.sleep(random.uniform(float(settle.min_s), float(settle.max_s)))

    click(config=click_cfg, controller=ctrl, press=press)

    if rand_cfg is not None and not rand_before:
        random_mouse(cfg=rand_cfg, controller=ctrl, bounds=bounds)

    return end_pos

def random_mouse_movement(
    max_seconds=3.221,
    step_px=3,
    sleep_ms=20,
):
    end_time = time.time() + max_seconds

    while time.time() < end_time:
        dx = random.choice([step_px, -step_px, 0])
        dy = random.choice([step_px, -step_px, 0])

        pyautogui.moveRel(dx, dy, duration=0)

        time.sleep(sleep_ms / 1000)


if __name__ == "__main__":
    _log(f"\n🧪 ai_cursor SELF TEST\n{ICON_WARN} Niet bewegen met je muis 🙂\n")
    time.sleep(2)

    bounds = get_default_bounds()
    x1, y1, x2, y2 = bounds
    _log(f"{ICON_ACTION} Bounds: {bounds}")

    for i in range(6):
        p = (random.randint(x1 + 120, x2 - 120), random.randint(y1 + 120, y2 - 120))
        _log(f"{ICON_MOVE} Move {i+1}/6 → {ICON_POS} {p}")
        move_and_click(p, button="left")
        time.sleep(0.20)

    _log(f"\n{ICON_OK} klaar\n")

