from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.image_detection import detect_image

if __name__ == "__main__":
    bot_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    hit = detect_image("jagex.png", area_name="Bot_Area", bot_id=1, verbose="debug")
    print("HIT:", hit)
