# ============================================================
# SENSOR: Is Skilling
# ============================================================

from vision.colour_detection import detect_colour
from core.ansi import ANSIx


def is_skilling(bot_id=1, area="Skilling_Area", colour="Groen", threshold=0.008, verbose=False):

    pct = detect_colour(colour, area, threshold, bot_id=bot_id)
    hit = pct > 0

    if verbose:
        sensor_col = ANSIx.info("Skilling Status")
        area_col = ANSIx.wrap(area, "area")
        status = ANSIx.gevonden(hit)

        print(f"{sensor_col} | Area: {area_col} | Status: {status}")

    return hit


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=== SENSOR TEST ===")
    print("Result:", is_skilling(bot_id=1, verbose=True))


# cd C:\Users\Hesse\Desktop\Runescape
# python -m sensors.is_skilling