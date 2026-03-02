from __future__ import annotations

import sys
import time
from pathlib import Path

# ============================================================
# STANDALONE BOOTSTRAP (run from anywhere)
# ============================================================

ROOT = Path(__file__).resolve().parents[0]
if (ROOT / "core").exists():
    repo = ROOT
else:
    repo = ROOT
    for p in ROOT.parents:
        if (p / "core").exists():
            repo = p
            break

if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

# ============================================================
# IMPORTS
# ============================================================

from core.move_to_area import move_to_area, move_in_area

# ============================================================
# TESTS
# ============================================================

def main():
    print("\n🧪 TEST START\nNiet aan je muis zitten...\n")
    time.sleep(2)

    print("➡️ Test 1: move_to_area Info_Area bot 1")
    move_to_area("Info_Area", bot_id=1, padding=3, click=False)
    time.sleep(1)

    print("\n➡️ Test 2: move_in_area Info_Area bot 2 + click")
    move_in_area("Info_Area", bot_id=2, verbose=True, padding=3, click=True)
    time.sleep(1)

    print("\n➡️ Test 3: loop bots 1 t/m 4")
    for bid in (1, 2, 3, 4):
        print(f"\n🤖 Bot {bid}")
        move_in_area("Info_Area", bot_id=bid, verbose=True, padding=3, click=False)
        time.sleep(0.8)

    print("\n✅ TEST KLAAR\n")


if __name__ == "__main__":
    main()