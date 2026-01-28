import sys
from pathlib import Path

def ensure_project_root(*, marker_dirs=("core", "config"), max_up=6):
    """
    Zet project root in sys.path zodat imports altijd werken.
    Zoekt omhoog tot er mappen bestaan zoals core/ en config/.
    """
    here = Path(__file__).resolve()
    p = here

    for _ in range(max_up + 1):
        if all((p / d).exists() for d in marker_dirs):
            root = p
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            return root
        p = p.parent

    raise SystemExit("❌ Project root niet gevonden (verwacht core/ en config/).")
