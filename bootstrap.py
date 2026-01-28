import sys
from pathlib import Path

def add_root(root=None):
    root = Path(root).resolve() if root else Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root
