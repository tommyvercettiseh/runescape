import sys
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from core.click_image import click_image
from core.ai_cursor import click
from vision.image_detection import detect_image
from helpers.random_sleep import random_sleep
from core.move_to_area import move_in_area

# ============================================================
# ASSIST BANKING
# WAT: Opent de bank (als die nog niet open is).
# WAAROM: Betrouwbare bank-open flow met retries + 50/50 input variatie.
# ============================================================
from core.move_to_area import move_in_area
from core.ai_cursor import click
from core.click_image import click_image
from helpers.random_sleep import sleep_custom
from ai_keyboard import press_key   

def assist_hop_world(bot_id=1):
    move_in_area("Chat_Area", bot_id=bot_id, verbose=False, padding=3)
    click()
    random_sleep()
    press_key("q")

assist_hop_world(bot_id=1)   