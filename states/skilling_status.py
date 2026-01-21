# ============================================================
# BOOTSTRAP
# ============================================================
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from vision.colour_detection import detect_colour

# ============================================================
# SKILLING STATUS
# ============================================================
def is_skilling(bot_id, verbose=True):
    """
    Returns True if skilling activity is detected.
    """
    return detect_colour(
        "groen",
        "Skilling_Area",
        2,
        bot_id=bot_id,
        verbose=verbose,
    ) > 0


# ============================================================
# MAIN (standalone test)
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    VERBOSE = True

    result = is_skilling(bot_id=BOT_ID, verbose=VERBOSE)
    print("🟢 SKILLING" if result else "🔴 NOT SKILLING")
