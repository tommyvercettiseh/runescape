from __future__ import annotations

# ============================================================
# === START BOOTSTRAP ========================================
# Doel: zorg dat je project-root in sys.path staat als je deze
# file direct runt via: python vision/move_to_image.py
# Hierdoor werken imports zoals "from ai_cursor import ..."
# ============================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# === END BOOTSTRAP ==========================================
# ============================================================


# ============================================================
# === START IMPORTS ==========================================
# Doel: alle dependencies die deze module nodig heeft:
# move_cursor/click voor input
# detect_image voor vision matchen
# typing voor type hints
# random voor random target punt in bounding box
# ============================================================
from typing import Optional, Dict, List, Tuple
import random

from ai_cursor import move_cursor, click
from vision.image_detection import detect_image
# === END IMPORTS ============================================
# ============================================================


# ============================================================
# === START HELPERS ==========================================
# Doel: kies een doelpunt (tx, ty) binnen de gevonden bounding box.
# Deze helper wordt gebruikt door move_to_image.
# anchor:
#   "topleft" = linksboven van box
#   "center"  = midden van box
#   "random"  = random punt in box (met padding)
# ============================================================
def _pick_point_in_match(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    anchor: str,
    padding: int,
) -> Tuple[int, int]:
    if anchor == "topleft":
        return (x, y)

    if anchor == "random":
        pad = max(0, int(padding))
        x1 = x + pad
        y1 = y + pad
        x2 = x + width - pad
        y2 = y + height - pad

        # als padding groter is dan de box: fallback naar center
        if x2 <= x1 or y2 <= y1:
            return (x + width // 2, y + height // 2)

        return (random.randint(x1, x2), random.randint(y1, y2))

    # default: center
    return (x + width // 2, y + height // 2)
# === END HELPERS ============================================
# ============================================================

def pretty(msg: str, icon: str = "•"):
    print(f"{icon} {msg}")

# ============================================================
# === START MOVE_TO_IMAGE ====================================
# Functie: move_to_image
# Doel: zoek een template image binnen een area (met bot offsets),
# kies een punt in de match bounding box, en beweeg daarheen.
#
# Retour:
#   (x, y) als match gevonden is
#   None als niet gevonden
# ============================================================
def move_to_image(
    image_name: str,
    area_name: str,
    *,
    bot_id: int = 1,
    areas: Optional[Dict[str, List[int]]] = None,
    verbose: str = "short",
    anchor: str = "center",   # "center" | "random" | "topleft"
    padding: int = 2,
    dx: int = 0,
    dy: int = 0,
    duration: float = 0.55,
    fps: int = 144,
) -> Optional[Tuple[int, int]]:
    # 1) detecteer image in area -> Match (met x,y,width,height)
    hit = detect_image(
        image_name=image_name,
        area_name=area_name,
        bot_id=bot_id,
        areas=areas,
        verbose=verbose,
    )
    if not hit:
        return None

    # 2) kies target punt in bounding box (center/random/topleft)
    tx, ty = _pick_point_in_match(
        x=hit.x,
        y=hit.y,
        width=hit.width,
        height=hit.height,
        anchor=anchor,
        padding=padding,
    )

    # 3) micro correctie (handig als je net naast de image wil klikken)
    tx += int(dx)
    ty += int(dy)

    # 4) beweeg smooth naar target
    move_cursor((tx, ty), duration=duration, fps=fps)
    return (tx, ty)
# === END MOVE_TO_IMAGE ======================================
# ============================================================


# ============================================================
# === START CLICK_IMAGE ======================================
# Functie: click_image
# Doel: wrapper boven move_to_image -> als image gevonden is:
# beweeg ernaartoe en klik. Return True/False.
# ============================================================
def click_image(
    image_name: str,
    area_name: str,
    *,
    bot_id: int = 1,
    areas: Optional[Dict[str, List[int]]] = None,
    verbose: str = "short",
    anchor: str = "center",
    padding: int = 2,
    dx: int = 0,
    dy: int = 0,
    duration: float = 0.55,
    fps: int = 144,
    delay: float = 0.03,
    button: str = "left",
) -> bool:
    pos = move_to_image(
        image_name=image_name,
        area_name=area_name,
        bot_id=bot_id,
        areas=areas,
        verbose=verbose,
        anchor=anchor,
        padding=padding,
        dx=dx,
        dy=dy,
        duration=duration,
        fps=fps,
    )
    if not pos:
        return False

    click(button=button, delay=delay)
    return True
# === END CLICK_IMAGE ========================================
# ============================================================


# ============================================================
# === START CLI TEST =========================================
# Doel: snel testen vanuit terminal:
# python vision/move_to_image.py
# Test:
#   1) move_to_image naar jagex.png in Bot_Area
#   2) click_image op dezelfde target
# ============================================================

if __name__ == "__main__":
    import time

    print("\n🧪 MOVE TO IMAGE TEST")
    print("────────────────────────────")
    pretty("Niet bewegen met je muis", "⚠️")
    time.sleep(2)

    print("\n▶ MOVE_TO_IMAGE")
    print("────────────────────────────")
    pos = move_to_image(
        "jagex.png",
        "Bot_Area",
        bot_id=1,
        anchor="random",
        verbose="short",
        duration=0.65,
        fps=144,
    )
    pretty(f"Position     = {pos}", "📍")
    time.sleep(0.8)

    print("\n▶ CLICK_IMAGE")
    print("────────────────────────────")
    for i in (3, 2, 1):
        pretty(f"Click in {i}", "⏳")
        time.sleep(1)

    ok = click_image(
        "jagex.png",
        "Bot_Area",
        bot_id=1,
        anchor="random",
        verbose="short",
        duration=0.65,
        fps=144,
        delay=0.05,
        button="left",
    )

    pretty(f"Click_image = {ok}", "✅" if ok else "❌")
    print("\n────────────────────────────")
