from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from states.hp_status import enough_HP
from core.helpers.assist_eat_food import eat_food


DEFAULT_FOOD_IMAGES = [
    "Item_Shrimp.png",
    "Item_Anchovies.png",
    "Item_Sardine.png",
    "Item_Trout.png",
    "Item_Salmon.png",
    "Item_Tuna.png",
    "Item_Lobster.png",
    "Item_Swordfish.png",
    "Item_Monkfish.png",
    "Item_Shark.png",
    "Item_MantaRay.png",
]


def assist_health(
    *,
    bot_id=1,
    food_images=None,
    verbose=True,
):
    """
    Assist functie:
    - gebruikt bestaande hp_status
    - eet automatisch bij low HP
    - default foodlijst ingebouwd
    """

    if enough_HP(bot_id=bot_id, verbose=False):
        verbose and print("❤️   HP 🟢")
        return True

    verbose and print("🆘 Low HP → Eat!")

    ate = eat_food(
        bot_id=bot_id,
        Item_images=food_images or DEFAULT_FOOD_IMAGES,
        verbose=verbose,
    )

    return ate


# ============================================================
# MAIN (standalone test)
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    VERBOSE = True

    print("🧪  Test assist_health")

    result = assist_health(
        bot_id=BOT_ID,
        verbose=VERBOSE,
    )

    print("RESULT:", result)
