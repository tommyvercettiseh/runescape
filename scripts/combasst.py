from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.autoload import get_exports

exports = get_exports(verbose=True)
print("\nTOTAL:", len(exports))
print("has detect_image:", "detect_image" in exports)
print("has assist_click_tab:", "assist_click_tab" in exports)
print("has should_play:", "should_play" in exports)
