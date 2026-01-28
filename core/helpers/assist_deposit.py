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
# ASSIST BANKING
# ============================================================
def deposit_inventory(
    bot_id=1,
    verbose=True,
):
    
    BANK_OPEN_IMG = "Bank_Deposit.png"
    AREA = "Bot_Area"

    # 🔍 Bank al open?
    if detect_image(BANK_OPEN_IMG, AREA, bot_id, verbose=False):
        if verbose:
            print("✅ 🏦 Bank is al open ")
            click_image(BANK_OPEN_IMG, "Bot_Area", bot_id, verbose=False)

# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":
    BOT_ID = 1
    print("🧪 Test assist_banking")

    # voorbeeld: max 6 seconden wachten
    result = deposit_inventory(bot_id=BOT_ID)

    print("RESULT:", result)
