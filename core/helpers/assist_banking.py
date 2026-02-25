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
from core.helpers.assist_target import assist_target

# ============================================================
# ASSIST BANKING 🏦
# ============================================================
def assist_banking(bot_id=1, verbose=True, timeout_s=10, poll_interval_s=1.22, attempts=1):
    BANK_OPEN_IMG = "Bank_Deposit.png"
    AREA = "Bot_Area"

    verbose and print(f"🏦 Assist_Banking() | BOT_ID={bot_id} verbose={verbose} timeout_s={timeout_s}s attempts={attempts}")

    # 🔍 Bank al open?
    if detect_image(BANK_OPEN_IMG, AREA, bot_id, verbose=False):
        verbose and print("🏦 Bank status: AL OPEN ✅")
        return True

    # ⏳ Wachten tot bank open (max timeout_s)
    def wait_for_bank_open():
        deadline = time.time() + timeout_s
        check_i = 0

        while time.time() < deadline:
            if detect_image(BANK_OPEN_IMG, AREA, bot_id, verbose=False):
                return True

            check_i += 1
            verbose and print(f"🏦 Waiting for bank... check={check_i} ⏳")
            time.sleep(poll_interval_s)

        return False

    # 🔁 Pogingen
    for attempt in range(attempts):
        verbose and print(f"🏦 Open attempt {attempt + 1}/{attempts} 🔁")

        assist_target(
            kleur="cyaan",
            area="Bot_Area",
            bot_id=bot_id,
            min_size=100,
            deep_erode_px=15,
            max_passes=1,
            verbose=False,
        )

        # ✅ Check resultaat
        if wait_for_bank_open():
            verbose and print("🏦 Bank succesvol geopend ✅")
            return True

        verbose and print("🏦 Geen bank gedetecteerd → retry ⏳")

    verbose and print("🏦 Bank openen mislukt ❌")
    return False


# ============================================================
# MAIN TEST 🧪
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    print("🧪 Test assist_banking")

    result = assist_banking(bot_id=BOT_ID, timeout_s=6)

    print(f"📊 Result → {'SUCCESS ✅' if result else 'FAILED ❌'}")