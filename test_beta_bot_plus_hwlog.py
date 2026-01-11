from __future__ import annotations
import time
import random
from datetime import datetime

from core.ai_cursor_beta import move_and_click, get_default_bounds, PynputExecutor
from core.executors.logged_executor import LoggedExecutor
from core.recorders.hardware_recorder import HardwareRecorder

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
bot_path = f"logs/bot_{stamp}.jsonl"
hw_path  = f"logs/hw_{stamp}.jsonl"

print("\n🧪 BETA + BOTLOG + HWLOG")
print("Niet aan je muis zitten 😄")
time.sleep(2)

hw = HardwareRecorder(hw_path, src="hw", log_moves=False).start()
ex = LoggedExecutor(PynputExecutor(), bot_path, src="beta")

bounds = get_default_bounds()
x1, y1, x2, y2 = bounds

for i in range(6):
    x = random.randint(x1 + 150, x2 - 150)
    y = random.randint(y1 + 150, y2 - 150)
    print(f"Move {i+1}/6 → ({x},{y})")
    move_and_click((x, y), executor=ex)
    time.sleep(0.25)

time.sleep(0.5)  # geef OS tijd om laatste click event te loggen
hw.stop()

print("\n✅ Klaar")
print("BOT:", bot_path)
print("HW :", hw_path)
