from __future__ import annotations

import sys
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_cursor import move_and_click
from vision.image_detection import detect_image, detect_images


def _normalize_png(name):
    name = (name or "").strip()
    if not name:
        return name
    return name if name.lower().endswith(".png") else name + ".png"


def _rand_point_in_hit(hit, padding):
    x = int(hit.x)
    y = int(hit.y)
    w = int(hit.width)
    h = int(hit.height)

    pad = max(0, int(padding))

    x1 = x + pad
    y1 = y + pad
    x2 = x + max(1, w) - pad
    y2 = y + max(1, h) - pad

    if x2 <= x1 or y2 <= y1:
        x1, y1, x2, y2 = x, y, x + max(1, w), y + max(1, h)

    cx = random.randint(x1, max(x1, x2 - 1))
    cy = random.randint(y1, max(y1, y2 - 1))
    return cx, cy


def click_image(image_name, area_name, bot_id=1, button="left", padding=2, verbose=True):
    img = _normalize_png(image_name)

    hit = detect_image(img, area_name, bot_id=bot_id, verbose=verbose)
    if not hit:
        return False

    cx, cy = _rand_point_in_hit(hit, padding)

    if verbose:
        print(
            f"🖱️ click_image {img} in {area_name} bot={bot_id} @ ({cx},{cy}) | "
            f"vorm={hit.vorm:.2f} kleur={hit.kleur:.2f}"
        )

    move_and_click((cx, cy), button=button)
    return True


def click_images(
    image_name,
    area_name,
    bot_id=1,
    button="left",
    padding=2,
    verbose=True,
    max_clicks=60,
    pattern=None,          # None = random kiezen
    row_band_px=18,
    exclude_slots=None,
):
    img = _normalize_png(image_name)
    hits = detect_images(img, area_name, bot_id=bot_id, verbose=verbose, max_hits=max_clicks)

    if not hits:
        if verbose:
            print("⚠️ geen hits")
        return []

    band = max(6, int(row_band_px))
    exclude = set(exclude_slots or [])

    def row_id(h):
        return int(h.y // band)

    # -------------------------
    # patronen
    # -------------------------
    def pattern_row(lr=True):
        rows = {}
        for h in hits:
            rows.setdefault(row_id(h), []).append(h)

        ordered = []
        for rk in sorted(rows.keys()):
            row_hits = sorted(rows[rk], key=lambda h: int(h.x))
            if not lr:
                row_hits.reverse()
            ordered.extend(row_hits)
        return ordered

    def pattern_snake(start_lr=True):
        rows = {}
        for h in hits:
            rows.setdefault(row_id(h), []).append(h)

        ordered = []
        row_keys = sorted(rows.keys())
        for i, rk in enumerate(row_keys):
            row_hits = sorted(rows[rk], key=lambda h: int(h.x))
            flip = (i % 2 == 1)
            if not start_lr:
                flip = not flip
            if flip:
                row_hits.reverse()
            ordered.extend(row_hits)
        return ordered

    PATTERNS = {
        "row": lambda: pattern_row(lr=True),
        "row_rev": lambda: pattern_row(lr=False),
        "snake": lambda: pattern_snake(start_lr=True),
        "snake_rev": lambda: pattern_snake(start_lr=False),
    }

    # -------------------------
    # kies patroon
    # -------------------------
    if pattern is None:
        pattern_name = random.choice(list(PATTERNS.keys()))
    else:
        pattern_name = pattern
        if pattern_name not in PATTERNS:
            raise ValueError(f"Onbekend pattern: {pattern_name}")

    ordered = PATTERNS[pattern_name]()

    if verbose:
        print(f"🧩 click_images patroon: {pattern_name} | hits={len(ordered)}")

    # -------------------------
    # klikken
    # -------------------------
    clicked = []
    for idx, h in enumerate(ordered):
        if idx in exclude:
            if verbose:
                print(f"⏭️ skip idx={idx}")
            continue

        x = int(h.x)
        y = int(h.y)
        w = int(h.width)
        hgt = int(h.height)

        pad = max(0, int(padding))
        x1 = x + pad
        y1 = y + pad
        x2 = x + max(1, w) - pad
        y2 = y + max(1, hgt) - pad

        if x2 <= x1 or y2 <= y1:
            x1, y1, x2, y2 = x, y, x + w, y + hgt

        cx = random.randint(x1, max(x1, x2 - 1))
        cy = random.randint(y1, max(y1, y2 - 1))

        if verbose:
            print(f"🖱️ idx={idx} @ ({cx},{cy}) vorm={h.vorm:.2f} kleur={h.kleur:.2f}")

        move_and_click((cx, cy), button=button)
        clicked.append((cx, cy))

    if verbose:
        print(f"✅ klaar | clicks={len(clicked)}")

    return clicked


if __name__ == "__main__":
    
    # 1 klik
    click_image("Close_Screen_X", "Bot_Area", bot_id=1, verbose=True)

    click_images("Item_Gold_Ore", "Inventory_Area", bot_id=1, verbose=True)

    # alles klikken in SNAKE patroon
    # click_images("Smiley.png", "Inventory_Area_Pattern", bot_id=1, pattern="snake", max_clicks=28)

    # row patroon (gewoon L->R elke rij)
    # click_images("Smiley.png", "Inventory_Area_Pattern", bot_id=1, pattern="row", max_clicks=28)

    # skip bv eerste slot
    # click_images("Smiley.png", "Inventory_Area_Pattern", bot_id=1, pattern="snake", exclude_slots={0})
