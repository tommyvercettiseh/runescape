from core.helpers.actions.click_colour import click_colour
from core.ansi import ANSIx


def click_target(bot_id=1, blob=400, verbose=True, area="Bot_Area", padding=4):

    ok, _ = click_colour("paars","Bot_Area",bot_id=bot_id,padding=padding,nearest_mouse=True,nearest_weighted=True,blob=blob,debug=False,trace_on=False,do_click=True)

    if verbose:
        print(ANSIx.ok(f"🎯 Click target | ✅ paars | blob={blob} | bot {bot_id}") if ok else ANSIx.fail(f"🎯 Click target | ❌ paars not found | blob={blob} | bot {bot_id}"))

    return ok


if __name__ == "__main__":
    print("🧪 Test click_target\n")
    result = click_target(bot_id=1, blob=200, verbose=True)
    print("\n📊 RESULT:", ANSIx.ok("✅ CLICKED") if result else ANSIx.fail("❌ NO HIT"))


# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.combat.click_target