import sys
from pathlib import Path
import random

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
# WAT: Opent de bank (als die nog niet open is).
# WAAROM: Betrouwbare bank-open flow met retries + 50/50 input variatie.
# ============================================================
def assist_banking(bot_id=1, verbose=True):
    BANK_OPEN_IMG = "Bank_Deposit.png"
    TARGET_IMG = "Cyaan.png"
    AREA = "Bot_Area"

    # 🔍 1) Eerst checken of bank al open is
    if detect_image(BANK_OPEN_IMG, AREA, bot_id, verbose=False):
        if verbose:
            print("🏦 Bank is al open ✅")
        return True

    # 🔁 2) Probeer openen
    for attempt in range(2):
        if verbose:
            print(f"🏦 Bank openen, poging {attempt + 1}/2")

        use_right = random.random() < 0.5

        # 🎲 50/50: rightclick of leftclick
        if use_right:
            if verbose:
                print("🖱️ Open via RIGHT click (50/50)")
            clicked = click_image(TARGET_IMG, AREA, bot_id, button="right", verbose=False)

            # rightclick kan menu openen → dan nog 1x links “bevestigen”
            if clicked:
                if verbose:
                    print("🖱️ Follow-up LEFT click (na rightclick)")
                    random_sleep()
                    click_image("Banking_Bank_Booth", AREA, bot_id, verbose=False)
                    random_sleep()
        else:
            if verbose:
                print("🖱️ Open via LEFT click (50/50)")
            clicked = click_image(TARGET_IMG, AREA, bot_id, verbose=False)
            random_sleep()

        # ✅ 3) Wachten tot bank open is (max ~10 sec: 5 checks)
        for check in range(5):
            if detect_image(BANK_OPEN_IMG, AREA, bot_id, verbose=False):
                if verbose:
                    print("🏦 Bank open ✅")
                return True

            if verbose:
                print(f"⏳ Wachten ({check + 1}/5)")
            random_sleep()

    if verbose:
        print("❌ Bank openen mislukt")
    return False


# ============================================================
# MAIN TEST
# WAT: Snelle lokale test-run.
# WAAROM: Checken of bank open detect + click flow werkt.
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1
    print("🧪 Test assist_banking")
    result = assist_banking(bot_id=BOT_ID, verbose=True)
    print("RESULT:", result)
