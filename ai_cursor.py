from __future__ import annotations

import time
import pyautogui

# ai_cursor is DOM:
# geen areas
# geen bot offsets
# geen config imports
# alleen bewegen en klikken


def move_cursor(pos: tuple[int, int], duration: float = 0.15) -> None:
    x, y = pos
    pyautogui.moveTo(int(x), int(y), duration=float(duration))


def click(button: str = "left", delay: float = 0.05) -> None:
    time.sleep(float(delay))
    pyautogui.click(button=button)


def move_and_click(pos: tuple[int, int], duration: float = 0.15, delay: float = 0.05, button: str = "left") -> None:
    move_cursor(pos, duration=duration)
    click(button=button, delay=delay)
