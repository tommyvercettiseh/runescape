from pathlib import Path
import time
import pyautogui

out_dir = Path("screenshots")
out_dir.mkdir(exist_ok=True)

ts = time.strftime("%Y%m%d_%H%M%S")
path = out_dir / f"desktop_{ts}.png"

img = pyautogui.screenshot()
img.save(path)

print("saved:", path.resolve())
