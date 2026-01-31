from __future__ import annotations

import sys
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.click_image import click_image
from vision.image_detection import detect_image


def eat_food(
    *,
    bot_id=1,
    Item_images=None,
    area="Inventory_Area",
    attempts=3,
    verbose=True,
):
    """
    Klikt het eerste eetbare item dat gevonden wordt.
    Ontbrekende images worden netjes overgeslagen.
    """

    if not Item_images:
        Item_images = [
            "Item_Shrimp.png",
            "Item_Trout.png",
            "Item_Salmon.png",
            "Item_Lobster.png",
            "Item_Swordfish.png",
            "Item_Monkfish.png",
            "Item_Shark.png",
        ]

    verbose and print("⏳  🍗  Zoeken naar voedsel")

    for attempt in range(int(attempts)):
        random.shuffle(Item_images)
        verbose and print(f"⏳  🍗  Poging {attempt + 1}/{attempts}")

        for img in Item_images:
            try:
                found = detect_image(img, area, bot_id, verbose=False)
            except FileNotFoundError:
                verbose and print(f"⚠️  🖼️  Image ontbreekt     | {img}")
                continue

            if found:
                verbose and print(f"✅  🍗  Gegeten             | {img}")
                click_image(img, area, bot_id, verbose=False)
                return True

    verbose and print("❌  🍗  Geen voedsel gevonden")
    return False


# ============================================================
# TEST 🧪
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1

    print("🧪  Test eat_food\n")

    result = eat_food(
        bot_id=BOT_ID,
        Item_images=[
            "Item_Trout.png",
            "Item_Salmon.png",
            "Item_Lobster.png",
        ],
        area="Inventory_Area",
        attempts=2,
        verbose=True,
    )

    print("\n📊  RESULTAAT:", "✅  SUCCES" if result else "❌  GEFAALD")
