from __future__ import annotations
import time
import random
from datetime import datetime

from core.ai_cursor_beta import move_and_click, get_default_bounds
from core.executors.arduino_executor import ArduinoExecutor
from core.executors.logged_executor import LoggedExecutor
from core.recorders.hardware_recorder import HardwareRecorder

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
bot_path = f"logs/bot_{stamp}.jsonl"
hw_path  = f"logs/hw_{stamp}.jsonl"

print("\n🧪 BETA + ARDUINO EXECUTOR + LOGS")
print("Niet aan je muis zitten 😄")
time.sleep(2)

hw = HardwareRecorder(hw_path, src="hw", log_moves=True).start()

arduino = ArduinoExecutor(port="COM6", baud=115200)
ex = LoggedExecutor(arduino, bot_path, src="arduino")

bounds = get_default_bounds()
x1, y1, x2, y2 = bounds

for i in range(6):
    x = random.randint(x1 + 200, x2 - 200)
    y = random.randint(y1 + 200, y2 - 200)
    print(f"Move {i+1}/6 → ({x},{y})")
    move_and_click((x, y), executor=ex)
    time.sleep(0.35)

time.sleep(0.6)
hw.stop()
arduino.close()

print("\n✅ Klaar")
print("BOT:", bot_path)
print("HW :", hw_path)
