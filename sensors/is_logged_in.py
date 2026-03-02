from vision.image_detection import detect_image

def is_logged_in(bot_id=1, verbose=False):
    hit = detect_image("xp.png", "Info_Area", bot_id=bot_id, verbose=False)
    result = hit is not None

    if verbose:
        print(f"{'🟢 Logged in' if result else '🔴 Not logged in'}")

    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("=== LOGIN TEST ===")
    result = is_logged_in(bot_id=1, verbose=True)
    print("Result:", result)

# python -m sensors.is_logged_in