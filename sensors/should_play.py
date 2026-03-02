from vision.colour_detection import detect_colour

def should_play(bot_id=1, verbose=False):
    pct = detect_colour("groen", "Antiban_Area", 80, bot_id=bot_id, verbose=False)
    result = pct > 0

    if verbose:
        print(f"{'🟢 Should play' if result else '🔴 Should NOT play'}")

    return result
# ============================================================
if __name__ == "__main__":
    print("=== SHOULD PLAY TEST ===")
    result = should_play(bot_id=1, verbose=True)
    print("Result:", result)

    # python -m sensors.should_play