# ============================================================
# BOOTSTRAP
# ============================================================
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.colour_detection import detect_colour
from helpers.log import log

def should_play(*, bot_id=1, area="Antiban_Area", min_pct=80, verbose=True, trace=False):
    pct = detect_colour(
        "groen",
        area,
        min_pct,
        bot_id=bot_id,
        verbose="off"
    )

    if pct > 0:
        log(verbose, "🟢 Should play", trace)
        return True

    log(verbose, "🔴 Should NOT play", trace)
    return False


# ============================================================
# STANDALONE TEST
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1

    print("\n=== SHOULD PLAY TEST ===")
    result = should_play(
        bot_id=BOT_ID,
        verbose=True,
        trace=True
    )

    print(f"\nResult → {result}")
