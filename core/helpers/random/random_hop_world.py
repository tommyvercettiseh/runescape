import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS 📥
# ============================================================
from core.move_to_area import move_in_area
from core.ai_cursor import click
from helpers.random_sleep import sleep_custom
from ai_keyboard import press_key

# ============================================================
# ASSIST HOP WORLD 🌍
# ============================================================
def assist_hop_world(bot_id=1, verbose=True):
    verbose and print("⏳  🌍  World hop starten")

    # Focus op chat area
    move_in_area("Chat_Area", bot_id=bot_id, verbose=False, padding=3)
    click()
    sleep_custom(0.12, 2.00)

    verbose and print("⏳  🌍  World hop key indrukken   | Q")
    press_key("q")

    # Wachten tot hop klaar is
    sleep_custom(8.12, 10.00)

    verbose and print("✅  🌍  World hop afgerond")
    return True


# ============================================================
# TEST 🧪
# ============================================================
if __name__ == "__main__":
    print("🧪  Test assist_hop_world\n")
    assist_hop_world(bot_id=1, verbose=True)
