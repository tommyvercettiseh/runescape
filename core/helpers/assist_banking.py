import sys
from pathlib import Path
import random
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from core.click_image import click_image
from vision.image_detection import detect_image
from helpers.random_sleep import random_sleep

# ============================================================
# ASSIST BANKING
# ============================================================
def assist_banking(
    bot_id=1,
    verbose=True,
    timeout_s=10,
    poll_interval_s=2,
    attempts=2,
):
    BANK_OPEN_IMG = "Bank_Deposit.png"
    TARGET_IMG = "Cyaan.png"
    AREA = "Bot_Area"

    # 🔍 Bank al open?
    if detect_image(BANK_OPEN_IMG, AREA, bot_id, verbose=False):
        if verbose:
            print("🏦 Bank is al open ✅")
        return True

    # ⏳ Wachten tot bank open (max timeout_s)
    def wait_for_bank_open():
        deadline = time.time() + timeout_s
        check_i = 0

        while time.time() < deadline:
            if detect_image(BANK_OPEN_IMG, AREA, bot_id, verbose=False):
                return True

            check_i += 1
            if verbose:
                print(f"⏳ Wachten ({check_i})")

            random_sleep()
            time.sleep(poll_interval_s)

        return False

    # 🔁 Pogingen
    for attempt in range(attempts):
        if verbose:
            print(f"🏦 Bank openen, poging {attempt + 1}/{attempts}")

        use_right = random.random() < 0.5

        # 🎲 50/50 click
        if use_right:
            if verbose:
                print("🖱️ RIGHT click")
            clicked = click_image(TARGET_IMG, AREA, bot_id, button="right", verbose=False)

            if clicked:
                random_sleep()
                click_image("Banking_Bank_Booth", AREA, bot_id, verbose=False)
                random_sleep()
        else:
            if verbose:
                print("🖱️ LEFT click")
            click_image(TARGET_IMG, AREA, bot_id, verbose=False)
            random_sleep()

        # ✅ Check resultaat
        if wait_for_bank_open():
            if verbose:
                print("🏦 Bank open ✅")
            return True

        if verbose:
            print("🔁 Timeout, retry")

    if verbose:
        print("❌ Bank openen mislukt")
    return False


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":
    BOT_ID = 1
    print("🧪 Test assist_banking")

    # voorbeeld: max 6 seconden wachten
    result = assist_banking(bot_id=BOT_ID, timeout_s=6)

    print("RESULT:", result)
