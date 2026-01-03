from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

__all__ = []
_load_errors: dict[str, str] = {}

PACKAGE_PATH = Path(__file__).parent
PACKAGE_NAME = __name__

for m in pkgutil.iter_modules([str(PACKAGE_PATH)]):
    mod_name = m.name
    if not mod_name.endswith("_status"):
        continue

    try:
        mod = importlib.import_module(f"{PACKAGE_NAME}.{mod_name}")
    except Exception as e:
        _load_errors[mod_name] = f"{type(e).__name__}: {e}"
        continue

    func_name = mod_name.removesuffix("_status")
    fn = getattr(mod, func_name, None)

    if callable(fn):
        globals()[func_name] = fn
        __all__.append(func_name)
    else:
        _load_errors[mod_name] = f"Geen callable '{func_name}' gevonden in module"

def debug_states() -> None:
    print(" states debug")
    print(" exports:", __all__)
    if _load_errors:
        print(" load errors:")
        for k, v in _load_errors.items():
            print(f"   {k}: {v}")
