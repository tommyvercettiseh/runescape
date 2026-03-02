# ============================================================
# SENSOR: Players Nearby (cyan dots on minimap)
# ============================================================

from vision.colour_detection import detect_colour
from core.ansi import ANSIx


def players_nearby(bot_id=1, area="Map_Area", colour="#00FFFF", verbose=True):

    hit = bool(detect_colour(colour, area, bot_id=bot_id))

    if verbose:
        status = ANSIx.gevonden(hit)
        area_col = ANSIx.wrap(area, "area")
        sensor_col = ANSIx.info("Players Nearby")

        print(f"{sensor_col} | Area: {area_col} | Status: {status}")

    return hit

if __name__ == "__main__":
    players_nearby(bot_id=1, verbose=True)

# cd C:\Users\Hesse\Desktop\Runescape
# python -m sensors.players_nearby