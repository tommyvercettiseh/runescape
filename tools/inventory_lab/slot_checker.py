from __future__ import annotations

from core.ansi import ANSIx
from tools.inventory_lab.slot_scan import scan_slots, load_cfg


def slot_checker(bot_id=1, verbose=True, empty_bg_pct=None, pad=None):

    cfg = load_cfg()
    r = scan_slots(
        bot_id=bot_id,
        area=cfg.get("area", "Inventory_Area"),
        empty_bg_pct=empty_bg_pct,   # None = pak saved value
        pad=pad,                     # None = pak saved value
        debug=False,
    )

    filled = r["filled_count"]
    empty = r["empty_count"]

    used_bg = r["empty_bg_pct"]
    used_pad = r.get("pad", cfg.get("pad"))

    if verbose:
        print(ANSIx.info(f"🎒 Slot checker | bot {bot_id} | filled={filled} empty={empty} total={r['slots_total']} | bg_pct={used_bg:.2f} | pad={used_pad}"))
        print(ANSIx.ok(f"✅ Filled slots: {r['filled_slots']}") if filled else ANSIx.fail("⚠️ No filled slots detected"))
        print(ANSIx.ok(f"✅ Empty slots:  {r['empty_slots']}") if empty else ANSIx.fail("⚠️ No empty slots detected"))

    return r


if __name__ == "__main__":
    print("🧪 Slot checker\n")

    # ✅ default = gebruikt laatste SAVE uit de UI
    slot_checker(bot_id=1, verbose=True)

    # 🔧 wil je handmatig testen?
    # slot_checker(bot_id=1, verbose=True, empty_bg_pct=0.55, pad=10)


# cd C:\Users\Hesse\Desktop\Runescape
# python -m tools.inventory_lab.slot_checker