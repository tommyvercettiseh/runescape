from __future__ import annotations
import time
import math
from pynput.mouse import Controller, Button
import random
import pyautogui

mouse = Controller()

def _ease(t: float) -> float:
    # smooth in/out
    return 2*t*t if t < 0.5 else 1 - ((-2*t + 2) ** 2) / 2

def move_cursor(pos: tuple[int, int], duration: float = 0.35, fps: int = 120) -> None:
    x2, y2 = int(pos[0]), int(pos[1])
    x1, y1 = mouse.position

    duration = max(0.08, float(duration))
    steps = max(12, int(duration * fps))
    dt = duration / steps

    for i in range(1, steps + 1):
        t = i / steps
        s = _ease(t)
        x = int(x1 + (x2 - x1) * s)
        y = int(y1 + (y2 - y1) * s)
        mouse.position = (x, y)
        time.sleep(dt)

    mouse.position = (x2, y2)

def click(button: str = "left", delay: float = 0.03) -> None:
    time.sleep(float(delay))
    if button == "right":
        mouse.click(Button.right, 1)
    else:
        mouse.click(Button.left, 1)

def move_and_click(pos: tuple[int, int], duration: float = 0.35, delay: float = 0.03, button: str = "left") -> None:
    move_cursor(pos, duration=duration)
    click(button=button, delay=delay)

if __name__ == "__main__":


    print("\n🧪 ai_cursor SELF TEST\nNiet bewegen met je muis 🙂\n")
    time.sleep(2)

    w, h = pyautogui.size()
    for _ in range(4):
        p = (random.randint(200, w - 200), random.randint(200, h - 200))
        move_cursor(p, duration=0.55, fps=144)
        time.sleep(0.25)

    print("\n✅ klaar\n")
