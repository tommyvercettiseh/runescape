import pyautogui
import numpy as np

from core.bot_offsets import load_areas, apply_offset

BOT_ID = 1
AREA_NAME = "Focus Area"

areas = load_areas()
box = apply_offset(areas[AREA_NAME], BOT_ID)
x1, y1, x2, y2 = box

img = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
arr = np.array(img)

print("area:", AREA_NAME)
print("bot:", BOT_ID)
print("box:", box)
print("shape:", arr.shape)
