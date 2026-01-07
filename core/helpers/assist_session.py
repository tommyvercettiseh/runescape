from __future__ import annotations

import sys
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.image_detection import detect_image
from core.helpers.assist_login import assist_login
from core.helpers.assist_logout import assist_logout

def is_logged_in(bot_id=1):
    return detect_image("xp.png", "Info_Area", bot_id=bot_id, verbose=False)

def is_logged_out(bot_id=1):
    return detect_image("Login_Screen_World.png", "Bot_Area_Full", bot_id=bot_id, verbose=False)

def ensure_session(bot_id=1, verbose=True, want_logged_in=True, timeout=25):
    """
    want_logged_in=True  -> zorg dat je ingelogd bent
    want_logged_in=False -> zorg dat je uitgelogd bent
    """
    start = time.time()

    while time.time() - start < timeout:
        if want_logged_in:
            if is_logged_in(bot_id):
                if verbose: print("✅ Session ok: ingelogd")
                return True
            if verbose: print("🔑 Login nodig")
            return assist_login(bot_id=bot_id, timeout=20, verbose=verbose)

        else:
            if is_logged_out(bot_id):
                if verbose: print("✅ Session ok: uitgelogd")
                return True
            if verbose: print("🚪 Logout nodig")
            return assist_logout(bot_id=bot_id, timeout=15, verbose=verbose)

    if verbose:
        print("⚠️ ensure_session timeout")
    return False
# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    BOT = 1

    print("🧪 TEST ensure_session (login -> logout)")

    print("\n➡️ LOGIN test")
    ok_login = ensure_session(bot_id=BOT, verbose=True, want_logged_in=True)
    print("LOGIN RESULT:", ok_login)

    print("\n⏳ Wachten 5 sec...")
    time.sleep(5)

    print("\n➡️ LOGOUT test")
    ok_logout = ensure_session(bot_id=BOT, verbose=True, want_logged_in=False)
    print("LOGOUT RESULT:", ok_logout)

    print("\n⏳ Wachten 2 sec...")
    time.sleep(2)

    print("\n➡️ LOGIN test (nog een keer)")
    ok_login2 = ensure_session(bot_id=BOT, verbose=True, want_logged_in=True)
    print("LOGIN2 RESULT:", ok_login2)

    print("\n✅ TEST klaar")
