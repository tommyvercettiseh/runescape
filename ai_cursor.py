# === START BOOTSTRAP ===
# WAT: Module voor muisbewegingen + klikken (primitives).
# WAAROM: Houd input-gedrag centraal en herbruikbaar; wrappers combineren primitives.
# === END BOOTSTRAP ===


# === START IMPORTS ===
from __future__ import annotations
import time
import random
from dataclasses import dataclass
from typing import Optional, Tuple, Literal

import pyautogui
from pynput.mouse import Controller, Button
# === END IMPORTS ===


# === START CONSTANTS ===
# WAT: Defaults + vaste iconen voor scanbare logging.
# WAAROM: Geen magic values door de code heen; makkelijk aanpasbaar zonder refactor.

ICON_ACTION = "▶"
ICON_OK = "✅"
ICON_WARN = "⚠️"
ICON_POS = "📍"
ICON_MOVE = "🧭"

MouseButton = Literal["left", "right"]
Point = Tuple[int, int]
# === END CONSTANTS ===


# === START MODELS ===
# WAT: Config models voor cursorgedrag.
# WAAROM: Dynamisch instelbaar (duur, FPS, min steps) zonder hardcoding in functies.

@dataclass(frozen=True)
class CursorMotionConfig:
    duration: float = 0.35
    fps: int = 120
    min_duration: float = 0.08
    min_steps: int = 12


@dataclass(frozen=True)
class ClickConfig:
    delay: float = 0.03
    button: MouseButton = "left"
# === END MODELS ===


# === START HELPERS ===
# WAT: Kleine hulpfuncties (easing, clamps, logging).
# WAAROM: Houd core logic schoon en herbruikbaar.

def _ease_in_out_quad(t: float) -> float:
    """Smooth in/out easing (0..1 → 0..1)."""
    return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2


def _clamp_duration(duration: float, min_duration: float) -> float:
    return max(float(min_duration), float(duration))


def _compute_steps(duration: float, fps: int, min_steps: int) -> int:
    fps = max(1, int(fps))
    return max(int(min_steps), int(duration * fps))


def _log(msg: str) -> None:
    print(msg)
# === END HELPERS ===


# === START CORE LOGIC ===
# WAT: Pure muis-primitives: bewegen + klikken.
# WAAROM: Deze laag bevat geen project-specifieke aannames; eenvoudig te testen/hergebruiken.

def move_cursor(
    pos: Point,
    *,
    config: CursorMotionConfig = CursorMotionConfig(),
    controller: Optional[Controller] = None,
) -> Point:
    """
    Beweegt cursor vloeiend naar pos.

    Returns:
        Eindpositie (x, y)
    """
    ctrl = controller or Controller()

    x2, y2 = int(pos[0]), int(pos[1])
    x1, y1 = ctrl.position

    duration = _clamp_duration(config.duration, config.min_duration)
    steps = _compute_steps(duration, config.fps, config.min_steps)
    dt = duration / steps if steps > 0 else 0.0

    for i in range(1, steps + 1):
        t = i / steps
        s = _ease_in_out_quad(t)
        x = int(x1 + (x2 - x1) * s)
        y = int(y1 + (y2 - y1) * s)
        ctrl.position = (x, y)
        time.sleep(dt)

    ctrl.position = (x2, y2)
    return (x2, y2)


def click(
    *,
    config: ClickConfig = ClickConfig(),
    controller: Optional[Controller] = None,
) -> None:
    """Klikt met left/right muisknop met optionele delay."""
    ctrl = controller or Controller()

    time.sleep(float(config.delay))
    if config.button == "right":
        ctrl.click(Button.right, 1)
    else:
        ctrl.click(Button.left, 1)
# === END CORE LOGIC ===


# === START API ===
# WAT: Wrapper API die primitives combineert (geen nieuwe logica).
# WAAROM: Convenience-functies voor veelgebruikte acties zonder duplicatie.

def move_and_click(
    pos: Point,
    *,
    motion: CursorMotionConfig = CursorMotionConfig(),
    click_cfg: ClickConfig = ClickConfig(),
    controller: Optional[Controller] = None,
) -> Point:
    """Beweeg naar pos en klik. Returns eindpositie."""
    ctrl = controller or Controller()
    end_pos = move_cursor(pos, config=motion, controller=ctrl)
    click(config=click_cfg, controller=ctrl)
    return end_pos
# === END API ===


# === START CLI TEST ===
# WAT: Veilige self-test (random bewegingen binnen scherm).
# WAAROM: Snel checken of input werkt zonder externe afhankelijkheden.

if __name__ == "__main__":
    _log(f"\n🧪 ai_cursor SELF TEST\n{ICON_WARN} Niet bewegen met je muis 🙂\n")
    time.sleep(2)

    w, h = pyautogui.size()

    # Dynamische margin zodat het op kleine schermen ook werkt
    margin = max(20, min(w, h) // 10)

    motion = CursorMotionConfig(duration=0.55, fps=144)
    ctrl = Controller()

    _log(f"{ICON_ACTION} Scherm: {w}x{h} | margin={margin}")
    for i in range(4):
        p = (random.randint(margin, w - margin), random.randint(margin, h - margin))
        _log(f"{ICON_MOVE} Move {i+1}/4 → {ICON_POS} {p}")
        move_cursor(p, config=motion, controller=ctrl)
        time.sleep(0.25)

    _log(f"\n{ICON_OK} klaar\n")
# === END CLI TEST ===
