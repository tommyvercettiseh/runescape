import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pyautogui
from vision.image_detection import detect_one


if __name__ == "__main__":
    # gebruikt automatisch presets uit config/templates_meta.json
    hit = detect_one("jagex.png", area_name="FullScreen", bot_id=1)
    print(hit)

    if hit:
        pyautogui.moveTo(hit.x + hit.width // 2, hit.y + hit.height // 2)
        # pyautogui.click(hit.x + hit.width // 2, hit.y + hit.height // 2)
