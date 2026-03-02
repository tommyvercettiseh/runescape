from __future__ import annotations
from core.click_image import click_image


def deposit_inventory(bot_id=1, area="Bot_Area", verbose=False):
    image = "Bank_Deposit.png"

    ok = click_image(image, area, bot_id=bot_id, verbose=False)

    if verbose:
        print("🏦 Deposit | ✅ Geklikt" if ok else "🏦 Deposit | ❌ Knop niet gevonden")
    return ok


# ============================================================
# SIMPLE TEST MAIN
# ============================================================
if __name__ == "__main__":
    print("🧪 Banking | Deposit inventory")
    result = deposit_inventory(bot_id=1, area="Bot_Area", verbose=True)
    print("📌 Result:", result)


# RUN:
# python -m core.helpers.banking.assist_deposit