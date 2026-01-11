from __future__ import annotations
import time
import random

# 👇 gebruik expliciet de beta
from core.ai_cursor_beta import move_and_click, get_default_bounds  

print("\n🧪 AI CURSOR BETA TEST")
print("Niet bewegen met je muis 😄")
time.sleep(2)

bounds = get_default_bounds()
x1, y1, x2, y2 = bounds

print("Bounds:", bounds)

for i in range(8):
    x = random.randint(x1 + 150, x2 - 150)
    y = random.randint(y1 + 150, y2 - 150)

    print(f"Move {i+1}/8 → ({x},{y})")
    move_and_click((x, y))

    time.sleep(0.3)

print("\n✅ Test klaar")
