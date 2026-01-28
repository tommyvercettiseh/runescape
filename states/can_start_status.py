# ============================================================
# BOOTSTRAP
# ============================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # Runescape/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
import time

from helpers.log import log
from states.should_play_status import should_play
from states.logged_in_status import logged_in
from core.helpers.assist_login import assist_login
from core.helpers.assist_logout import assist_logout


# ============================================================
# CAN START
# ============================================================
def can_start(*, bot_id=1, verbose=False, trace=False):
    want_logged_in = should_play(bot_id=bot_id, verbose=verbose, trace=trace)
    is_in = logged_in(bot_id=bot_id, verbose=verbose, trace=trace)

    if want_logged_in and is_in:
        log(verbose, "🟢 Can start", trace)
        return True

    if not want_logged_in:
        if is_in:
            log(verbose, "🟡 Should not be logged in → logging out", trace)
            assist_logout(bot_id=bot_id, verbose=verbose)
        else:
            log(verbose, "🛑 Not allowed to play", trace)
        return False

    log(verbose, "🔐 Not logged in → logging in", trace)
    assist_login(bot_id=bot_id, verbose=verbose)

    time.sleep(1.2)

    if logged_in(bot_id=bot_id, verbose=verbose, trace=trace):
        log(verbose, "✅ Login successful → can start", trace)
        return True

    log(verbose, "🔴 Login failed → cannot start", trace)
    return False


# ============================================================
# STANDALONE TEST
# ============================================================
if __name__ == "__main__":
    print("\n=== CAN START TEST ===")
    print("Result =", can_start(bot_id=1, verbose=False, trace=False))
