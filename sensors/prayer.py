# ============================================================
# SENSOR: Low Prayer
# ============================================================

from vision.colour_detection import detect_colour
from core.ansi import ANSIx


def low_prayer(bot_id=1, area="Prayer", verbose=False):

    red = detect_colour("rood", area, 10, bot_id=bot_id) > 0
    green = detect_colour("groen", area, 10, bot_id=bot_id) > 0

    result = red or not green  # rood = low, geen groen = ook low

    if verbose:
        sensor_col = ANSIx.info("Prayer Status")
        area_col = ANSIx.wrap(area, "area")
        status = ANSIx.fail("LOW") if result else ANSIx.ok("OK")

        print(f"{sensor_col} | Area: {area_col} | Status: {status}")

    return result

# ============================================================
if __name__ == "__main__":
    print("Test Prayer sensor...")
    result = low_prayer(bot_id=1, verbose=True)

    if result:
        print("👉 Actie: DRINK PRAYER POT")
    else:
        print("👉 Actie: SAFE")


# cd C:\Users\Hesse\Desktop\Runescape
# python -m sensors.prayer