from vision.image_detection import detect_image
from core.ansi import ANSIx


BANK_IMAGE = "Bank_Deposit.png"
BANK_AREA = "Bot_Area"   # pas aan als jouw bank ergens anders zit


def is_bank_open(bot_id: int = 1, verbose: bool = False) -> bool:
    hit = detect_image(BANK_IMAGE, BANK_AREA, bot_id=bot_id, verbose=False)
    result = hit is not None

    if verbose:
        if result:
            print(ANSIx.ok(f"🏦 Bank OPEN | Bot {bot_id}"))
        else:
            print(ANSIx.fail(f"🏦 Bank CLOSED | Bot {bot_id}"))

    return result

# ============================================================
if __name__ == "__main__":
    print("=== BANK STATUS TEST ===\n")
    result = is_bank_open(bot_id=1, verbose=True)

    status = ANSIx.ok("✅ BANK OPEN") if result else ANSIx.fail("❌ BANK CLOSED")
    print("\n📊 RESULT:", status)


# cd C:\Users\Hesse\Desktop\Runescape
# python -m sensors.bank_open