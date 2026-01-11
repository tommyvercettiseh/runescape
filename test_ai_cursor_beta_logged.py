from __future__ import annotations
import time
import random

from core.ai_cursor_beta import move_and_click, get_default_bounds, PynputExecutor
from core.executors.logged_executor import LoggedExecutor

print("\n🧪 BETA + LOG TEST")
print("Niet bewegen met je muis 😄")
time.sleep(2)

ex = LoggedExecutor(PynputExecutor(), "logs/bot_events.jsonl", src="beta")

bounds = get_default_bounds()
x1, y1, x2, y2 = bounds

for i in range(6):
    x = random.randint(x1 + 150, x2 - 150)
    y = random.randint(y1 + 150, y2 - 150)
    print(f"Move {i+1}/6 → ({x},{y})")
    move_and_click((x, y), executor=ex)
    time.sleep(0.25)

print("\n✅ Klaar. Check: logs/bot_events.jsonl")
