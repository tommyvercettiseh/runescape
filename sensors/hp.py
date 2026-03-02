from vision.colour_detection import detect_colour
from core.ansi import ANSIx


def low_hp(bot_id=1, area="HP_Area", verbose=False):

    red = detect_colour("rood", area, 10, bot_id=bot_id) > 0
    orange = detect_colour("oranje", area, 10, bot_id=bot_id) > 0
    green = detect_colour("groen", area, 10, bot_id=bot_id) > 0

    result = red or orange or not green

    if verbose:
        sensor_col = ANSIx.info("HP Status")
        area_col = ANSIx.wrap(area, "area")
        status = ANSIx.fail("LOW") if result else ANSIx.ok("OK")

        print(f"{sensor_col} | Area: {area_col} | Status: {status}")

    return result


# python -m sensors.hp

if __name__ == "__main__":
    print("Test HP sensor...")
    result = low_hp(bot_id=1, verbose=True)

    print("👉 Actie: EAT" if result else "👉 Actie: SAFE")