# ============================================================
# SENSOR: Random Event
# ============================================================

from vision.image_detection import detect_image
from core.ansi import ANSIx


def has_random_event(bot_id=1, area="Chat_Area", image="Notification_Random_Event.png", verbose=False):

    hit = detect_image(image, area, bot_id=bot_id) is not None

    if verbose:
        sensor_col = ANSIx.info("Random Event")
        area_col = ANSIx.wrap(area, "area")
        status = ANSIx.fail("DETECTED") if hit else ANSIx.ok("CLEAR")

        print(f"{sensor_col} | Area: {area_col} | Status: {status}")

    return hit

# ============================================================
if __name__ == "__main__":
    print("Test Random Event sensor...")
    result = has_random_event(bot_id=1, verbose=True)
    print("👉 Actie: HANDLE EVENT" if result else "👉 Actie: CONTINUE")


# cd C:\Users\Hesse\Desktop\Runescape
# python -m sensors.random_event