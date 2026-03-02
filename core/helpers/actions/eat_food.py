from __future__ import annotations

import random
from pathlib import Path

from core.click_image import click_image
from vision.image_detection import detect_image

# Gebruik jouw centrale images map (pas aan als je elders IMAGES_DIR hebt)
ROOT = Path(__file__).resolve()
for p in [ROOT] + list(ROOT.parents):
    if (p / "assets" / "images").exists():
        IMAGES_DIR = p / "assets" / "images"
        break
else:
    IMAGES_DIR = None


def _exists_image(name: str) -> bool:
    if IMAGES_DIR is None:
        return True  # fallback: geen pad gevonden, probeer gewoon
    return (IMAGES_DIR / name).exists()


def eat_food(
    *,
    bot_id=1,
    item_images=None,
    area="Inventory_Area",
    verbose=False,
):
    default_items = [
        "Item_Shrimp.png",
        "Item_Trout.png",
        "Item_Salmon.png",
        "Item_Lobster.png",
        "Item_Swordfish.png",
        "Item_Monkfish.png",
        "Item_Shark.png",
    ]

    items = list(item_images) if item_images else list(default_items)

    # ✅ filter op bestaande files
    items = [x for x in items if x and _exists_image(x)]

    if not items:
        if verbose:
            print("❌  🍗  Geen food templates aanwezig in assets/images")
        return False

    random.shuffle(items)

    if verbose:
        print(f"⏳  🍗  Zoeken naar voedsel | {len(items)} templates")

    for img in items:
        if not detect_image(img, area, bot_id=bot_id, verbose=False):
            continue

        clicked = click_image(img, area, bot_id=bot_id, verbose=False)
        if clicked:
            if verbose:
                print(f"✅  🍗  Geklikt | {img}")
            return True

        if verbose:
            print(f"⚠️  🍗  Found maar click faalde | {img}")

    if verbose:
        print("❌  🍗  Geen voedsel gevonden / klik faalde")
    return False