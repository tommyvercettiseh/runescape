from __future__ import annotations

from core.move_to_area import move_in_area
from helpers.random_sleep import sleep_custom
from core.helpers.assist_click_tab import assist_click_tab
from core.ansi import ANSIx

# onthoud rotatie per bot + skillset
_XP_ROT_STATE: dict[str, int] = {}


def assist_check_experience(*areas: str, bot_id: int = 1, verbose: bool = True) -> bool:
    # =========================
    # INPUT CLEANUP 🧹
    # =========================
    cleaned: list[str] = []
    for a in areas:
        s = str(a).strip()
        if s:
            cleaned.append(s)

    if not cleaned:
        verbose and print(ANSIx.fail("📊 XP check | geen skill opgegeven"))
        return False

    # =========================
    # PICK: 1 skill = die, 2+ = roteren 🔁
    # =========================
    if len(cleaned) == 1:
        area = cleaned[0]
    else:
        key = f"{bot_id}|" + "|".join(cleaned)
        i = _XP_ROT_STATE.get(key, 0) % len(cleaned)
        area = cleaned[i]
        _XP_ROT_STATE[key] = i + 1

    verbose and print(ANSIx.info(f"📊 XP check | {area} | bot {bot_id}"))

    # =========================
    # ACTION 🎯
    # =========================
    ok = assist_click_tab("Skilling", bot_id=bot_id, verbose=False, timeout=3.0)
    if not ok:
        verbose and print(ANSIx.fail("🧭 Tab | Skilling | failed"))
        return False
    verbose and print(ANSIx.ok("🧭 Tab | Skilling"))

    ok = move_in_area(area, bot_id=bot_id, verbose=False)
    if not ok:
        verbose and print(ANSIx.fail(f"📌 Hover XP | {area} | failed"))
        return False
    verbose and print(ANSIx.ok(f"📌 Hover XP | {area}"))

    sleep_custom(1.5, 4.3)

    ok = assist_click_tab("Inventory", bot_id=bot_id, verbose=False, timeout=3.0)
    if not ok:
        verbose and print(ANSIx.fail("🎒 Tab | Inventory | failed"))
        return False
    verbose and print(ANSIx.ok("🎒 Tab | Inventory"))

    return True


if __name__ == "__main__":
    print("🧪 Test assist_check_experience\n")

    assist_check_experience("Crafting", bot_id=1, verbose=True)

    print("\n🔁 Rotatie test\n")
    assist_check_experience("Woodcutting", "Fishing", bot_id=1, verbose=True)

# cd C:\Users\Hesse\Desktop\Runescape 
# python -m core.helpers.random.check_experience