import sys
from pathlib import Path
from time import sleep

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.click_image import click_image
from core.helpers.assist_logout import assist_logout
from core.helpers.assist_login import assist_login

BOT_ID = 1


print("🧪 TEST: assist_logout (bot 1)")
result = assist_login(bot_id=BOT_ID, timeout=20)
print("assist_login:", result)
