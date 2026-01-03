# ============================================================
# BOOTSTRAP
# ============================================================
from __future__ import annotations

import sys
from pathlib import Path
from time import time, sleep

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from core.click_image import click_image
from vision.image_detection import detect_image

# ============================================================
# MAIN
# ============================================================
def assist_login(*, bot_id: int = 1, timeout: float = 15.0, verbose: bool = False) -> bool:
    start = time()

    if verbose:
        print(f"🔐 Logging in (bot {bot_id})")

    while time() - start < timeout:
        if detect_image(image_name="xp.png", area_name="Info_Area", bot_id=bot_id, verbose="off"):
            if verbose:
                print("✅ We zijn ingelogd!")
            return True

        if click_image("Login_Screen_Play_Now.png", "Bot_Area", bot_id, verbose="off"):
            if verbose:
                print("🖱️ Play Now (rood) aangeklikt")
            sleep(0.9)

        elif click_image("Login_Screen_Play_Now_Red.png", "Bot_Area_Full", bot_id, verbose="off"):
            if verbose:
                print("🖱️ Play Now aangeklikt")
            sleep(0.9)

        sleep(0.25)

    if verbose:
        print("⚠️ Inloggen niet gelukt binnen timeout")
    return False
