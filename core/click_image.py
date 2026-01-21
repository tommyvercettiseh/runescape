from __future__ import annotations

import sys
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_cursor import move_and_click
from vision.image_detection import detect_images
from helpers.log import log


def _normalize_png(name):
    name = (name or "").strip()
    if not name:
        return name
    return name if name.lower().endswith(".png") else name + ".png"


def _rand_point_in_hit(hit, padding):
    x = int(getattr(hit, "x", 0))
    y = int(getattr(hit, "y", 0))
    w = int(getattr(hit, "width", 1))
    h = int(getattr(hit, "height", 1))

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


def _first_hit(img, area_name, bot_id, max_hits=1):
    hits = detect_images(img, area_name, bot_id=bot_id, verbose=False, max_hits=max_hits) or []
    return hits


def click_image(
    image_name,
    area_name,
    bot_id=1,
    button="left",
    padding=2,
    verbose=True,
    trace=False,
    trace_depth=5,
    debug=False,
):
    img = _normalize_png(image_name)

    # ✅ exact dezelfde detect pipeline als click_random_image
    hits = _first_hit(img, area_name, bot_id, max_hits=1)
    if not hits:
        log(verbose, f"⚠️ click_image geen hit | img={img} area={area_name} bot={bot_id}", trace, depth=trace_depth)
        return False

    hit = hits[0]
    cx, cy = _rand_point_in_hit(hit, padding)

    if debug:
        vorm = getattr(hit, "vorm", None)
        kleur = getattr(hit, "kleur", None)
        extra = ""
        if vorm is not None:
            extra += f" vorm={vorm:.2f}"
        if kleur is not None:
            extra += f" kleur={kleur:.2f}"
        log(verbose, f"🖱️ click_image | img={img} area={area_name} bot={bot_id} @ ({cx},{cy}){extra}", trace, depth=trace_depth)

    move_and_click((cx, cy), button=button)

    if debug:
        log(verbose, "✅ click_image done", trace, depth=trace_depth)

    return True


def click_random_image(
    image_name,
    area_name,
    bot_id=1,
    dry_run=False,
    seed=None,
    button="left",
    padding=2,
    verbose=True,
    max_hits=60,
    trace=False,
    trace_depth=5,
    debug=False,
):
    if seed is not None:
        random.seed(seed)

    img = _normalize_png(image_name)

    hits = _first_hit(img, area_name, bot_id, max_hits=max_hits)
    if not hits:
        log(verbose, f"⚠️ click_random_image geen hits | img={img} area={area_name} bot={bot_id}", trace, depth=trace_depth)
        return None

    hit = random.choice(hits)
    cx, cy = _rand_point_in_hit(hit, padding)

    if debug:
        mode = "Dry 🧪" if dry_run else "Live 🔥"
        vorm = getattr(hit, "vorm", None)
        kleur = getattr(hit, "kleur", None)
        extra = ""
        if vorm is not None:
            extra += f" vorm={vorm:.2f}"
        if kleur is not None:
            extra += f" kleur={kleur:.2f}"
        log(verbose, f"🎯 Random hit | img={img} | Mode={mode} | Pos=({cx},{cy}){extra}", trace, depth=trace_depth)

    if not dry_run:
        move_and_click((cx, cy), button=button)

    return (cx, cy)


if __name__ == "__main__":
    click_random_image(
        "Item_Willow_Logs",
        "Inventory_Area",
        bot_id=1,
        dry_run=False,
        trace=True,
        trace_depth=6,
        debug=True,
    )

    click_image(
        "Close_Screen_X",
        "Bot_Area",
        bot_id=1,
        trace=True,
        trace_depth=6,
        debug=True,
    )
