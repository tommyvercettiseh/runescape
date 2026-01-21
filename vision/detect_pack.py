from __future__ import annotations

from pathlib import Path
from core.paths import IMAGES_DIR
from vision.image_detection import detect_image

def detect_pack(
    label: str,
    pack: str,
    area_name: str,
    bot_id: int = 1,
    verbose: bool = False,
):
    d = Path(IMAGES_DIR) / label / pack
    if not d.exists():
        return None

    best = None
    for p in d.glob("*.png"):
        key = f"{label}/{pack}/{p.name}"
        h = detect_image(key, area_name, bot_id=bot_id, verbose=verbose)
        if not h:
            continue

        if best is None:
            best = h
            continue

        # kies beste op vorm, dan kleur
        if (h.vorm > best.vorm) or (h.vorm == best.vorm and h.kleur > best.kleur):
            best = h

    return best
