# ============================================================
# BOOTSTRAP (altijd eerst)
# ============================================================
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# SETTINGS
# ============================================================

VERBOSE = False
BOT_ID = 1
from vision.detect_pack import detect_pack

hit = detect_pack("fire", "active", "Bot_Area_Center", bot_id=1, verbose=True)
if hit:
    print("🔥 fire found", hit.x, hit.y, hit.vorm, hit.kleur)
