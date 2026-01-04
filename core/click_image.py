# === START BOOTSTRAP ===
# WAT: Zorgt dat project-root in sys.path staat zodat imports werken.
# WAAROM: Script kan overal gestart worden zonder import-issues.
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# === END BOOTSTRAP ===


# === START IMPORTS ===
# WAT: Laadt alle dependencies voor random timing, muis control en image detectie.
# WAAROM: Nodig om “menselijk” te bewegen en op gevonden images te klikken.
import random
import time
from dataclasses import replace

from pynput.mouse import Controller
from core.ai_cursor import move_and_click, CursorMotionConfig, ClickConfig
from vision.image_detection import detect_image
# === END IMPORTS ===


# === START ANSI ===
# WAT: ANSI kleuren voor console logging.
# WAAROM: Verbose output blijft scanbaar.
ANSI = {
    "green": "\033[92m",
    "red": "\033[91m",
    "cyan": "\033[96m",
    "purple": "\033[95m",
    "reset": "\033[0m",
}
# === END ANSI ===


# === START DEFAULTS ===
# WAT: Standaard configs voor cursor motion en click.
# WAAROM: Consistente basisinstellingen voor alle clicks.
DEFAULT_MOTION = CursorMotionConfig(duration=0.75, fps=85, min_duration=0.18, min_steps=22)
DEFAULT_CLICK = ClickConfig(delay=0.09, button="left")

_MOUSE = Controller()
# === END DEFAULTS ===


# === START HELPERS ===
# WAT: Kleine helpers voor bestandsnamen, human jitter, pauses en target punten.
# WAAROM: Houdt API functions kort en herbruikbaar.
def _png(name):
    name = (name or "").strip()
    return name if name.lower().endswith(".png") else f"{name}.png"


def _img_label(name):
    return _png(name)[:-4].upper()


def _jitter(v, pct, lo, hi):
    v = v * random.triangular(1 - pct, 1 + pct, 1.0)
    return max(lo, min(hi, v))


def _human_motion(m):
    return replace(
        m,
        duration=_jitter(m.duration, 0.22, m.min_duration, m.duration * 1.8),
        fps=_jitter(m.fps, 0.10, 60, 165),
        min_steps=_jitter(m.min_steps, 0.15, 12, 90),
    )


def _human_click(c):
    return replace(c, delay=_jitter(c.delay, 0.35, 0.04, 0.24))


def _micro_pause():
    if random.random() < 0.18:
        time.sleep(random.uniform(0.03, 0.12))


def _random_point(hit, padding):
    x1 = hit.x + padding
    y1 = hit.y + padding
    x2 = hit.x + hit.width - padding
    y2 = hit.y + hit.height - padding

    if x2 <= x1 or y2 <= y1:
        x1, y1 = hit.x, hit.y
        x2 = hit.x + hit.width
        y2 = hit.y + hit.height

    return random.randint(x1, x2 - 1), random.randint(y1, y2 - 1)


def _center_point(hit):
    return hit.x + hit.width // 2, hit.y + hit.height // 2


def _log(found, img, area, verbose):
    if not verbose:
        return

    if found:
        print(
            f"{ANSI['green']}🟢🖼️ Found{ANSI['reset']} | "
            f"{ANSI['cyan']}{img}{ANSI['reset']} in "
            f"{ANSI['purple']}{area}{ANSI['reset']}"
        )
    else:
        print(
            f"{ANSI['red']}🔴🖼️ Not found{ANSI['reset']} | "
            f"{ANSI['cyan']}{img}{ANSI['reset']} in "
            f"{ANSI['purple']}{area}{ANSI['reset']}"
        )
# === END HELPERS ===


# === START API ===
# WAT: Public functies om images te zoeken en (links/rechts) te klikken.
# WAAROM: Eén simpele interface voor alle click acties.
def click_image(image_name, area_name, bot_id=1, padding=2, button="left", verbose=False):
    image_name = _png(image_name)
    label = _img_label(image_name)

    hit = detect_image(image_name=image_name, area_name=area_name, bot_id=bot_id, verbose=False)
    if not hit:
        _log(False, label, area_name, verbose)
        return None

    _log(True, label, area_name, verbose)

    _micro_pause()
    target = _random_point(hit, padding)

    move_and_click(
        target,
        motion=_human_motion(DEFAULT_MOTION),
        click_cfg=_human_click(replace(DEFAULT_CLICK, button=button)),
        controller=_MOUSE,
    )
    return target


def click_image_center(image_name, area_name, bot_id=1, button="left", verbose=False):
    image_name = _png(image_name)
    label = _img_label(image_name)

    hit = detect_image(image_name=image_name, area_name=area_name, bot_id=bot_id, verbose=False)
    if not hit:
        _log(False, label, area_name, verbose)
        return None

    _log(True, label, area_name, verbose)

    _micro_pause()
    target = _center_point(hit)

    move_and_click(
        target,
        motion=_human_motion(DEFAULT_MOTION),
        click_cfg=_human_click(replace(DEFAULT_CLICK, button=button)),
        controller=_MOUSE,
    )
    return target
# === END API ===


# === START TEST ===
# WAT: Snelle lokale test-run voor links en rechts.
# WAAROM: Makkelijk checken of detect + click werkt.
if __name__ == "__main__":
    click_image("xp", "Info_Area", 1, verbose=True)                    # links (default)
    click_image("Cyaan", "Bot_Area", 1, button="right", verbose=True)    # rechts
# === END TEST ===
