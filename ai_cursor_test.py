# ============================================================
# START BOOTSTRAP
# ============================================================

from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# END BOOTSTRAP
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import time
import random
from dataclasses import dataclass
from pynput.mouse import Controller, Button
import pyautogui

# ============================================================
# CONFIG
# ============================================================

@dataclass(frozen=True)
class CursorMotionConfig:
    duration: float = 0.35
    fps: int = 120
    min_duration: float = 0.08
    min_steps: int = 12


@dataclass(frozen=True)
class ClickConfig:
    delay: float = 0.03
    button: str = "left"


# ============================================================
# HELPERS
# ============================================================

def _ease(t):
    return 2*t*t if t < 0.5 else 1 - ((-2*t + 2) ** 2) / 2


def _bezier(p0, p1, p2, t):
    return (
        (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t*t * p2[0],
        (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t*t * p2[1],
    )


# ============================================================
# CORE
# ============================================================

def move_cursor(pos, *, config=CursorMotionConfig(), controller=None):
    ctrl = controller or Controller()

    x1, y1 = ctrl.position
    x2, y2 = pos

    duration = max(config.min_duration, config.duration * random.uniform(0.75, 1.25))
    steps = max(config.min_steps, int(duration * config.fps))

    # bepaal of we 1 of 2 segmenten doen
    segments = random.choice([1, 2])

    points = [(x1, y1)]

    if segments == 2:
        mx = x1 + (x2 - x1) * random.uniform(0.3, 0.7)
        my = y1 + (y2 - y1) * random.uniform(0.3, 0.7)
        points.append((mx, my))

    points.append((x2, y2))

    steps_per_seg = steps // len(points)

    for idx in range(len(points) - 1):
        sx, sy = points[idx]
        ex, ey = points[idx + 1]

        # control point totaal willekeurig rond het pad
        cx = (sx + ex) / 2 + random.randint(-60, 60)
        cy = (sy + ey) / 2 + random.randint(-60, 60)

        for i in range(steps_per_seg):
            t = (i + 1) / steps_per_seg
            s = _ease(t)

            x, y = _bezier((sx, sy), (cx, cy), (ex, ey), s)

            # micro jitter
            x += random.uniform(-0.7, 0.7)
            y += random.uniform(-0.7, 0.7)

            ctrl.position = (int(x), int(y))
            time.sleep((duration / steps) * random.uniform(0.7, 1.4))

    # landing correctie
    if random.random() < 0.7:
        ctrl.position = (
            x2 + random.randint(-2, 2),
            y2 + random.randint(-2, 2),
        )
        time.sleep(random.uniform(0.01, 0.05))

    ctrl.position = (x2, y2)
    return (x2, y2)


def click(*, config=ClickConfig(), controller=None):
    ctrl = controller or Controller()
    time.sleep(config.delay * random.uniform(0.8, 1.4))
    ctrl.click(Button.right if config.button == "right" else Button.left, 1)


def move_and_click(pos, *, motion=CursorMotionConfig(), click_cfg=ClickConfig(), controller=None):
    ctrl = controller or Controller()
    move_cursor(pos, config=motion, controller=ctrl)
    click(config=click_cfg, controller=ctrl)
    return pos


# ============================================================
# SELF TEST ±5s
# ============================================================

if __name__ == "__main__":
    print("🧪 ai_cursor pattern-free test (5s) – handen weg 😄")
    time.sleep(1)

    w, h = pyautogui.size()
    margin = max(40, min(w, h) // 10)

    ctrl = Controller()
    motion = CursorMotionConfig(duration=0.45, fps=140)

    start = time.time()
    while time.time() - start < 5:
        p = (
            random.randint(margin, w - margin),
            random.randint(margin, h - margin),
        )
        move_cursor(p, config=motion, controller=ctrl)
        time.sleep(random.uniform(0.1, 0.25))

    print("✅ test klaar")
