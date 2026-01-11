from __future__ import annotations
import sys
from pathlib import Path

# ============================================================
# BOOTSTRAP
# ============================================================
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from vision.image_detection import detect_image

# ============================================================
# ASSIST INVENTORY
# ============================================================
def assist_inventory_empty(
    *,
    bot_id=1,
    area="Last_Inventory_Spot",
    empty_img="Empty_Last_Spot.png",
    verbose=True,
) -> bool:

    if detect_image(empty_img, area, bot_id=bot_id, verbose=False):
        if verbose:
            print("🎒 Inventory leeg 🟢")
        return True

    if verbose:
        print("🎒 Inventory is vol 🔴")
    return False


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    assist_inventory_empty(bot_id=1, verbose=True)
