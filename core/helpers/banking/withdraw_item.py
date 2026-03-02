from __future__ import annotations

import random
from core.click_image import click_image
from core.ansi import ANSIx


def withdraw_item(image, bot_id=1, area="Bot_Area", verbose=False):
    ok = click_image(image, area, bot_id=bot_id, verbose=False)
    if verbose:
        print(ANSIx.ok(f"🏦 Withdraw | ✅ {image}") if ok else ANSIx.fail(f"🏦 Withdraw | ❌ {image}"))
    return ok


def withdraw_items(images, bot_id=1, area="Bot_Area", random_order=False, verbose=False):
    items = list(images)

    if not items:
        verbose and print(ANSIx.fail("🏦 Withdraw | ❌ no items"))
        return False

    if random_order:
        random.shuffle(items)
        verbose and print(ANSIx.info(f"🔀 Withdraw order: {items}"))

    for img in items:
        ok = withdraw_item(img, bot_id=bot_id, area=area, verbose=verbose)
        if not ok:
            verbose and print(ANSIx.fail(f"⛔ Withdraw stopped | failed: {img}"))
            return False

    verbose and print(ANSIx.ok("🏦 Withdraw sequence done ✅"))
    return True


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    print("🧪 Banking | Withdraw items\n")

    BOT_ID = 1
    items = ["Item_Lobster.png", "Item_Willow_Logs.png"]

    print("Test 1: fixed order")
    ok1 = withdraw_items(items, bot_id=BOT_ID, area="Bot_Area", random_order=True, verbose=True)
    print("📌 Result:", ANSIx.ok("✅ SUCCESS") if ok1 else ANSIx.fail("❌ FAILED"))

# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.banking.withdraw_item