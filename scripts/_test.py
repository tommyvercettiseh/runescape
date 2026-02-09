# ============================================================
# BOOTSTRAP 📂
# ============================================================
from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# SETTINGS ⚙️
# ============================================================
BOT_ID = int(os.getenv("BOT_ID", "1"))
SKILL = os.getenv("SKILL", "Fishing").strip()

TRACE = False
VERBOSE = False
DEBUG = False

# ============================================================
# AUTOLOAD 🧠
# ============================================================
from core.autoload import autoload
autoload(globals(), verbose=VERBOSE)

# ✅ Scroll import (jouw nieuwe functie + config)
from core.ai_cursor import scroll, ScrollConfig

# ============================================================
# START 🧱
# ============================================================
def main():
    print("🧪 scroll test start")
    move_in_area("Bot_Area", bot_id=1, verbose=True, padding=3)

    scroll(
        direction="down",
        cfg=ScrollConfig(
            min_steps=8,
            max_steps=18,
            step_min=1,
            step_max=3,
            delay_min=0.18,
            delay_max=0.35,
            jitter_chance=0.08,
            jitter_min=1,
            jitter_max=1,
        ),
        speed_pct=100.0,
        verbose=True,
    )




    print("✅ scroll test done")


if __name__ == "__main__":
    main()
