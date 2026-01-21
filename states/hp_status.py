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
# HP STATUS
# ============================================================
def has_red_HP(bot_id, verbose=False):
    return detect_colour(
        "rood",
        "HP_Area",
        10,
        bot_id=bot_id,
        verbose=verbose,
    ) > 0


def has_green_HP(bot_id, verbose=False):
    return detect_colour(
        "groen",
        "HP_Area",
        10,
        bot_id=bot_id,
        verbose=verbose,
    ) > 0


def enough_HP(bot_id, verbose=False):
    """
    True  = genoeg HP
    False = eten / veilig spelen
    """
    if has_red_HP(bot_id, verbose):
        return False

    if has_green_HP(bot_id, verbose):
        return True

    # onzeker = liever veilig spelen
    return False


# ============================================================
# MAIN (standalone test)
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    VERBOSE = True

    print("🔴 RED HP:", has_red_HP(bot_id=BOT_ID, verbose=VERBOSE))
    print("🟢 GREEN HP:", has_green_HP(bot_id=BOT_ID, verbose=VERBOSE))
    print("❤️ ENOUGH HP:", enough_HP(bot_id=BOT_ID, verbose=VERBOSE))
