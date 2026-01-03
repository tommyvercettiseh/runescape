# ============================================================
# BOOTSTRAP
# ============================================================
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
import random
import time
from dataclasses import replace

from pynput.mouse import Controller
from core.ai_cursor import move_and_click, CursorMotionConfig, ClickConfig
from vision.image_detection import detect_image

# ============================================================
# DEFAULTS
# ============================================================
DEFAULT_MOTION = CursorMotionConfig(duration=0.75, fps=85, min_duration=0.18, min_steps=22)
DEFAULT_CLICK = ClickConfig(delay=0.09, button="left")

_MOUSE = Controller()

# ============================================================
# HELPERS
# ============================================================
def _normalize_image_name(name: str) -> str:
    name = (name or "").strip()
    return name if name.lower().endswith(".png") else f"{name}.png"

def _jitter(v, pct, lo, hi):
    v = v * random.triangular(1 - pct, 1 + pct, 1.0)
    return max(lo, min(hi, v))

def _human_motion(m):
    return replace(
        m,
        duration=_jitter(m.duration, 0.22, m.min_duration, m.duration * 1.8),
        fps=int(_jitter(m.fps, 0.10, 60, 165)),
        min_steps=int(_jitter(m.min_steps, 0.15, 12, 90)),
    )

def _human_click(c):
    return replace(c, delay=_jitter(c.delay, 0.35, 0.04, 0.24))

def _micro_pause():
    if random.random() < 0.18:
        time.sleep(random.uniform(0.03, 0.12))

def _random_point(hit, padding):
    x1 = int(hit.x + padding)
    y1 = int(hit.y + padding)
    x2 = int(hit.x + hit.width - padding)
    y2 = int(hit.y + hit.height - padding)

    if x2 <= x1 or y2 <= y1:
        x1, y1 = int(hit.x), int(hit.y)
        x2 = int(hit.x + hit.width)
        y2 = int(hit.y + hit.height)

    return random.randint(x1, x2 - 1), random.randint(y1, y2 - 1)

def _center_point(hit):
    return int(hit.x + hit.width / 2), int(hit.y + hit.height / 2)

# ============================================================
# API
# ============================================================
def click_image(image_name, area_name, bot_id=1, padding=2, verbose="short"):
    """
    click_image("xp", "Info_Area", 1)
    Altijd random klik binnen image bbox.
    """
    image_name = _normalize_image_name(image_name)

    hit = detect_image(image_name=image_name, area_name=area_name, bot_id=bot_id, verbose=verbose)
    if not hit:
        return None

    _micro_pause()
    target = _random_point(hit, padding)

    move_and_click(
        target,
        motion=_human_motion(DEFAULT_MOTION),
        click_cfg=_human_click(DEFAULT_CLICK),
        controller=_MOUSE,
    )
    return target


def click_image_center(image_name, area_name, bot_id=1, verbose="short"):
    """
    click_image_center("login", "Bot_Area", 1)
    Center klik.
    """
    image_name = _normalize_image_name(image_name)

    hit = detect_image(image_name=image_name, area_name=area_name, bot_id=bot_id, verbose=verbose)
    if not hit:
        return None

    _micro_pause()
    target = _center_point(hit)

    move_and_click(
        target,
        motion=_human_motion(DEFAULT_MOTION),
        click_cfg=_human_click(DEFAULT_CLICK),
        controller=_MOUSE,
    )
    return target


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    click_image("xp", "Info_Area", 1)
    click_image_center("xp", "Info_Area", 1)
