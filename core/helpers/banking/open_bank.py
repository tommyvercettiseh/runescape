import time
from sensors.bank_open import is_bank_open
from core.helpers.actions.click_colour import click_colour
from core.ansi import ANSIx


def open_bank(bot_id=1, timeout=6, verbose=True):

    # 🔍 Al open?
    if is_bank_open(bot_id=bot_id, verbose=False):
        verbose and print(ANSIx.ok(f"🏦 Bank already OPEN | bot {bot_id}"))
        return True

    verbose and print(ANSIx.info(f"🏦 Opening bank | bot {bot_id}"))

    # 🖱️ 1 klik
    ok, _ = click_colour("cyaan","Bot_Area",bot_id=bot_id,padding=4,nearest_mouse=True,nearest_weighted=True,blob=400,debug=False,trace_on=False,do_click=True)
    
    if not ok:
        verbose and print(ANSIx.fail(f"🏦 No bank colour found | bot {bot_id}"))
        return False

    verbose and print(ANSIx.ok(f"🖱️ Clicked cyaan | bot {bot_id}"))

    # ⏳ Wachten tot bank open wordt (max timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_bank_open(bot_id=bot_id, verbose=False):
            verbose and print(ANSIx.ok(f"🏦 Bank OPEN | bot {bot_id}"))
            return True
        time.sleep(0.1)

    verbose and print(ANSIx.fail(f"🏦 Bank still CLOSED | timeout {timeout}s | bot {bot_id}"))
    return False


if __name__ == "__main__":
    print("🧪 Test open_bank\n")
    result = open_bank(bot_id=1, timeout=6, verbose=True)
    print("\n📊 RESULT:", ANSIx.ok("✅ BANK OPEN") if result else ANSIx.fail("❌ BANK CLOSED"))


# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.banking.open_bank