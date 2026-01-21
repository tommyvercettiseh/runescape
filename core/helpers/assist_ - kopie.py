from __future__ import annotations
import sys
from pathlib import Path

# ============================================================

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ============================================================

from core.move_to_area import move_in_area
from helpers.random_sleep import sleep_custom  
from core.helpers.assist_click_tab import assist_click_tab

# ============================================================
def assist_check_experience(area, *, bot_id=1, verbose=True):
    area = str(area).strip()

    if verbose:
        print(f"🎯 Move in area: {area} (bot {bot_id})")

    assist_click_tab("Skilling", bot_id=bot_id, verbose=verbose, timeout=3.0)

    move_in_area(
        area,
        bot_id=bot_id,
        verbose=verbose,
    )
    sleep_custom(1.5, 4.3)

    assist_click_tab("Inventory", bot_id=bot_id, verbose=verbose, timeout=3.0)

    return True

# ============================================================
# TESTING
# ============================================================
if __name__ == "__main__":
    assist_check_experience("Woodcutting", bot_id=1, verbose=True)
