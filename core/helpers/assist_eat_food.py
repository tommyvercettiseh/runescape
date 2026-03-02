from __future__ import annotations

import random
from core.click_image import click_image
from vision.image_detection import detect_image


"""
============================================================
ACTION: EAT FOOD 🍗
============================================================
Doel
  Probeert 1 eetbaar item in de inventory te klikken.

Interface
  bot_id       : welke bot/client
  item_images  : lijst met mogelijke food images (optional)
  area         : inventory area naam
  verbose      : prints aan/uit

Return
  True  = gegeten
  False = niets gevonden

Regels
  Pure action: geen sensors, geen state, geen hp checks.
  Alleen detect → click → resultaat.
============================================================
"""


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
    random.shuffle(items)

    if verbose:
        print("⏳  🍗  Zoeken naar voedsel")

    for img in items:
        try:
            found = detect_image(img, area, bot_id=bot_id, verbose=False)
        except FileNotFoundError:
            if verbose:
                print(f"⚠️  🖼️  Image ontbreekt | {img}")
            continue

        if not found:
            continue

        if verbose:
            print(f"✅  🍗  Gegeten | {img}")

        click_image(img, area, bot_id=bot_id, verbose=False)
        return True

    if verbose:
        print("❌  🍗  Geen voedsel gevonden")

    return False


# ============================================================
# TEST 🧪
# ============================================================
if __name__ == "__main__":
    print("🧪  Test eat_food\n")

    result = eat_food(
        bot_id=1,
        item_images=[
            "Item_Trout.png",
            "Item_Salmon.png",
            "Item_Lobster.png",
        ],
        area="Inventory_Area",
        verbose=True,
    )

    print("\n📊  RESULTAAT:", "✅  SUCCES" if result else "❌  GEFAALD")