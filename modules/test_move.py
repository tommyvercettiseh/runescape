import sys
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ai_cursor
print("ai_cursor loaded from:", ai_cursor.__file__)

from ai_cursor import move_cursor

time.sleep(2)
move_cursor((800, 500), debug=True, force_slow=True)
