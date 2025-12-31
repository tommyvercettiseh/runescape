from __future__ import annotations

import sys
from pathlib import Path
import inspect

# ----------------------------
# Bootstrap: project-root in sys.path
# ----------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _try_import():
    from core.paths import CONFIG_DIR  # noqa
    from core.bot_offsets import BOT_OFFSETS, apply_offset, load_areas  # noqa
    return CONFIG_DIR, BOT_OFFSETS, apply_offset, load_areas


def _expect_offsets(bot_offsets: dict[int, tuple[int, int]]):
    exp = {1: (0, 0), 2: (958, 0), 3: (0, 498), 4: (958, 498)}
    ok = True
    for k, v in exp.items():
        got = bot_offsets.get(int(k))
        if got != v:
            print(f"❌ BOT_OFFSETS[{k}] = {got} verwacht {v}")
            ok = False
        else:
            print(f"✅ BOT_OFFSETS[{k}] = {got}")
    return ok


def _test_apply(apply_offset, bot_offsets):
    base = [100, 200, 400, 600]  # x1,y1,x2,y2
    ok = True

    for bot_id in (1, 2, 3, 4):
        out = apply_offset(base, bot_id)
        ox, oy = bot_offsets[int(bot_id)]
        exp = [base[0] + ox, base[1] + oy, base[2] + ox, base[3] + oy]

        if out != exp:
            print(f"❌ apply_offset bot {bot_id} -> {out} verwacht {exp}")
            ok = False
        else:
            print(f"✅ apply_offset bot {bot_id} -> {out}")

    return ok


def _test_areas(load_areas, config_dir: Path, bot_offsets, apply_offset):
    areas_path = Path(config_dir) / "areas.json"
    if not areas_path.exists():
        print(f"❌ areas.json niet gevonden op: {areas_path.resolve()}")
        return False

    areas = load_areas()
    if not isinstance(areas, dict) or not areas:
        print("❌ load_areas() geeft geen dict of is leeg")
        return False

    names = list(areas.keys())[:3]
    print(f"✅ areas loaded: {len(areas)} (samples: {names})")

    ok = True

    # check shape: elk coords moet list[4]
    for name in names:
        c = areas[name]
        if not (isinstance(c, list) and len(c) == 4):
            print(f"❌ area '{name}' is geen [x1,y1,x2,y2]. Kreeg: {c!r}")
            ok = False

    # check offset effect
    sample_name = names[0]
    sample = areas[sample_name]
    for bot_id in (1, 2, 3, 4):
        shifted = apply_offset(sample, bot_id)
        ox, oy = bot_offsets[int(bot_id)]
        exp = [sample[0] + ox, sample[1] + oy, sample[2] + ox, sample[3] + oy]

        if shifted != exp:
            print(f"❌ area offset faalt bot {bot_id} op '{sample_name}' -> {shifted} verwacht {exp}")
            ok = False

    if ok:
        print("✅ area offsets lijken correct (xyxy verschuift exact met BOT_OFFSETS)")
    return ok


def main():
    try:
        config_dir, bot_offsets, apply_offset, load_areas = _try_import()
    except Exception as e:
        print("❌ Import faalt:", repr(e))
        print("Tip: run vanuit project-root en importeer NOOIT vanuit package 'config'. Altijd via core.paths.")
        raise

    # Laat zien welke apply_offset je ECHT draait (handig voor debugging)
    import core.bot_offsets as m
    print("🔎 core.bot_offsets file:", m.__file__)
    print("🔎 apply_offset source:\n", inspect.getsource(m.apply_offset))

    bot_offsets = {int(k): tuple(v) for k, v in bot_offsets.items()}

    ok1 = _expect_offsets(bot_offsets)
    ok2 = _test_apply(apply_offset, bot_offsets)
    ok3 = _test_areas(load_areas, config_dir, bot_offsets, apply_offset)

    all_ok = ok1 and ok2 and ok3
    print("\nRESULT:", "✅ ALLES GOED" if all_ok else "❌ ER ZIT IETS SCHEEF")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
