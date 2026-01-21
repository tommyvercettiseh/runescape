# ============================================================
# BOOTSTRAP (altijd eerst)
# ============================================================
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS (na bootstrap)
# ============================================================
from states.can_start_status import can_continue

# ============================================================
# SETTINGS
# ============================================================
BOT_ID = 1
VERBOSE = True

# ============================================================
# LOOP
# ============================================================
while True:
    ok = can_continue(bot_id=BOT_ID, verbose=VERBOSE, do_actions=False)
    print("✅ CAN CONTINUE" if ok else "⛔ BLOCKED")
    time.sleep(1.0)
