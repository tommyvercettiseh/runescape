from vision.colour_detection import detect_colour

def is_skilling(bot_id, verbose=True):
    if detect_colour("green", "Skilling_Area", 2, bot_id=bot_id, verbose=verbose):
        return True

    # fallback: check rood en toon dat ook netjes
    detect_colour("red", "Skilling_Area", 2, bot_id=bot_id, verbose=verbose)
    return False
