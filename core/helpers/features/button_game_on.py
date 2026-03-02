from __future__ import annotations

from core.ansi import ANSIx
from vision.image_detection import detect_image
from core.click_image import click_image


IMAGE_ON = "Tab_Chat_Game_On.png"
IMAGE_OFF = "Tab_Chat_Game_Off.png"
AREA = "Chat_Buttons"


def button_game_on(bot_id: int = 1, verbose: bool = True) -> bool:
    # Staat al ON?
    if detect_image(IMAGE_ON, AREA, bot_id=bot_id, verbose=False):
        verbose and print(ANSIx.ok(f"🎮 Game tab | ON | bot {bot_id}"))
        return True

    # Klik OFF (maakt hem ON)
    clicked = click_image(IMAGE_OFF, AREA, bot_id=bot_id, verbose=False)
    if clicked:
        verbose and print(ANSIx.ok(f"🎮 Game tab | switched ON | bot {bot_id}"))
    else:
        verbose and print(ANSIx.fail(f"🎮 Game tab | OFF not found | bot {bot_id}"))
        return False

    # Verify (geen spam)
    if detect_image(IMAGE_ON, AREA, bot_id=bot_id, verbose=False):
        return True

    verbose and print(ANSIx.fail(f"🎮 Game tab | click done but still not ON | bot {bot_id}"))
    return False


if __name__ == "__main__":
    print("🧪 Test button_game_on\n")
    ok = button_game_on(bot_id=1, verbose=True)
    print("\n📊 RESULT:", ANSIx.ok("✅ GAME ON") if ok else ANSIx.fail("❌ GAME NOT SET"))

# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.features.button_game_on