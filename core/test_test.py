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
from typing import Optional, Tuple, Literal, Dict, List

from pynput.mouse import Controller

from ai_cursor import move_and_click, CursorMotionConfig, ClickConfig
from vision.image_detection import detect_image, Match

Point = Tuple[int, int]
Anchor = Literal["random", "center", "topleft"]

# ============================================================
# DEFAULT "HUMAN" FEEL (jij hoeft dit nooit mee te geven)
# ============================================================
DEFAULT_MOTION = CursorMotionConfig(
    duration=0.75,    # gemiddeld "menselijk"
    fps=85,
    min_duration=0.18,
    min_steps=22,
)
DEFAULT_CLICK = ClickConfig(
    delay=0.09,       # klik-hesitatie
    button="left",
)

# ============================================================
# HUMAN RANDOMIZER
# ============================================================
def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _human_jitter(
    base: float,
    *,
    pct: float = 0.18,
    lo: float | None = None,
    hi: float | None = None,
) -> float:
    """
    Menselijke variatie rond base.
    triangular => vaak rond normaal, soms afwijkend (menselijker dan uniform).
    """
    base = float(base)
    factor = random.triangular(1 - pct, 1 + pct, 1.0)
    val = base * factor

    if lo is not None:
        val = max(float(lo), val)
    if hi is not None:
        val = min(float(hi), val)
    return val


def humanize_motion(motion: CursorMotionConfig) -> CursorMotionConfig:
    """Variatie in duration, fps, min_steps."""
    dur = _human_jitter(
        motion.duration,
        pct=0.22,
        lo=getattr(motion, "min_duration", 0.08),
        hi=max(motion.duration * 1.8, getattr(motion, "min_duration", 0.08)),
    )

    fps0 = float(getattr(motion, "fps", 90))
    fps = int(_clamp(round(_human_jitter(fps0, pct=0.10, lo=60, hi=165)), 60, 165))

    steps0 = float(getattr(motion, "min_steps", 25))
    min_steps = int(_clamp(round(_human_jitter(steps0, pct=0.15, lo=12, hi=90)), 12, 90))

    return replace(motion, duration=dur, fps=fps, min_steps=min_steps)


def humanize_click(click_cfg: ClickConfig) -> ClickConfig:
    """Variatie in click delay."""
    delay0 = float(getattr(click_cfg, "delay", 0.08))
    delay = _human_jitter(delay0, pct=0.35, lo=0.04, hi=0.24)
    return replace(click_cfg, delay=delay)


def maybe_micro_pause(chance: float = 0.18) -> None:
    """Soms even mini-hesitatie voor de click."""
    if random.random() < chance:
        time.sleep(random.triangular(0.03, 0.12, 0.05))

# ============================================================
# HELPERS
# ============================================================
def _normalize_image_name(name: str) -> str:
    """Laat je 'xp' of 'xp.png' meegeven; wij fixen het."""
    s = (name or "").strip()
    if not s:
        return s
    return s if s.lower().endswith(".png") else f"{s}.png"

# ============================================================
# POINT PICKERS
# ============================================================
def _rand_in_bbox(hit: Match, *, padding: int = 2) -> Point:
    """Random punt binnen bbox (met padding)."""
    x1, y1 = int(hit.x), int(hit.y)
    x2, y2 = x1 + int(hit.width), y1 + int(hit.height)

    pad = max(0, int(padding))
    ix1, iy1 = x1 + pad, y1 + pad
    ix2, iy2 = x2 - pad, y2 - pad

    # als padding te groot is, val terug op hele bbox
    if ix2 <= ix1 or iy2 <= iy1:
        ix1, iy1, ix2, iy2 = x1, y1, x2, y2

    px = random.randint(ix1, ix2 - 1)
    py = random.randint(iy1, iy2 - 1)
    return (px, py)


def _pick_point(
    hit: Match,
    *,
    anchor: Anchor = "random",
    padding: int = 2,
    dx: int = 0,
    dy: int = 0,
) -> Point:
    """Kies target punt in bbox."""
    x1, y1 = int(hit.x), int(hit.y)
    x2, y2 = x1 + int(hit.width), y1 + int(hit.height)

    if anchor == "topleft":
        p = (x1, y1)
    elif anchor == "center":
        p = ((x1 + x2) // 2, (y1 + y2) // 2)
    else:
        p = _rand_in_bbox(hit, padding=padding)

    return (p[0] + int(dx), p[1] + int(dy))

# ============================================================
# MAIN API
# ============================================================
def click_image(
    image_name: str,
    area_name: str,
    bot_id: int = 1,
    *,
    areas: Optional[Dict[str, List[int]]] = None,
    anchor: Anchor = "random",
    padding: int = 2,
    dx: int = 0,
    dy: int = 0,
    controller: Optional[Controller] = None,
    verbose: str = "short",
    humanize: bool = True,
    micro_pause: bool = True,
    motion: Optional[CursorMotionConfig] = None,
    click_cfg: Optional[ClickConfig] = None,
) -> Optional[Point]:
    """
    Find image in area -> pick point in bbox -> move -> click

    Jij gebruikt meestal gewoon:
        click_image("xp", "Info_Area", 1)
        click_image("Cyaan", "Bot_Area", BOT_ID)

    Returns target point or None
    """
    img = _normalize_image_name(image_name)

    hit = detect_image(
        image_name=img,
        area_name=area_name,
        bot_id=bot_id,
        areas=areas,
        verbose=verbose,
    )
    if not hit:
        return None

    target = _pick_point(hit, anchor=anchor, padding=padding, dx=dx, dy=dy)

    # defaults (menselijk) + optioneel overridable
    m = motion or DEFAULT_MOTION
    c = click_cfg or DEFAULT_CLICK

    if humanize:
        m = humanize_motion(m)
        c = humanize_click(c)

    ctrl = controller or Controller()

    if micro_pause:
        maybe_micro_pause(chance=0.18)

    move_and_click(target, motion=m, click_cfg=c, controller=ctrl)
    return target

# ============================================================
# VOORBEELDEN
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1

    print("\n🧪 click_image voorbeelden\n")

    # 1) Simpel: bestandnaam zonder .png (wordt automatisch toegevoegd)
    print("1) basic: xp in Info_Area")
    click_image("xp", "Info_Area", BOT_ID, verbose="short")

    # 2) Ook oké met .png
    print("2) basic: xp.png in Info_Area")
    click_image("xp.png", "Info_Area", BOT_ID, verbose="short")

    # 3) Altijd midden van de match (handig voor kleine knoppen)
    print("3) center anchor")
    click_image("xp", "Info_Area", BOT_ID, anchor="center", verbose="short")

    # 4) Random maar met wat padding (klik niet exact op de rand)
    print("4) random met padding=3")
    click_image("xp", "Info_Area", BOT_ID, anchor="random", padding=3, verbose="short")

    # 5) Kleine offset (net onder of naast een icoon klikken)
    print("5) offset dx/dy")
    click_image("xp", "Info_Area", BOT_ID, dx=6, dy=10, verbose="short")

    # 6) Als je ooit even 'robot-fast' wil testen (meestal niet doen)
    print("6) humanize uit (test)")
    click_image("xp", "Info_Area", BOT_ID, humanize=False, micro_pause=False, verbose="short")

    print("\n🏁 klaar\n")
