from vision.colour_detection import detect_colour

def should_play(bot_id, verbose=False):
    return detect_colour("green","Antiban_Area",80,bot_id=bot_id,verbose=verbose)
