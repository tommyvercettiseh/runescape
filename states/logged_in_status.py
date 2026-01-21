from vision.image_detection import detect_image
from helpers.log import log

def logged_in(*, bot_id=1, area="Info_Area", image="xp.png", verbose=True, trace=False):
    hit = detect_image(
        image,
        area,
        bot_id=bot_id,
        verbose="off"
    )

    if hit is not None:
        log(verbose, "🟢 Logged in", trace)
        return True

    log(verbose, "🔴 Not logged in", trace)
    return False


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    BOT_ID = 1

    print("\n=== LOGGED IN TEST ===")
    result = logged_in(
        bot_id=BOT_ID,
        verbose=True,
        trace=True
    )

    print(f"\nResult → {result}")
