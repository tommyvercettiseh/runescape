from __future__ import annotations

import importlib
import pkgutil
from typing import Any, Dict

BOOL_FN_CANDIDATES = (
    "logged_in",
    "should_play",
    "is_skilling",
)

def collect_statuses(*, bot_id: int, verbose: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    errors: Dict[str, str] = {}

    pkg = importlib.import_module("states")

    for m in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        if m.ispkg:
            continue

        short = m.name.split(".")[-1]            # skilling_status
        if not short.endswith("_status"):
            continue
        key = short.replace("_status", "")       # skilling

        try:
            mod = importlib.import_module(m.name)

            # 1) Nieuwe stijl (optioneel): get_status -> dict
            fn = getattr(mod, "get_status", None)
            if callable(fn):
                res = fn(bot_id=bot_id, verbose=verbose) or {}
                out[res.get("name", key)] = res.get("value")
                continue

            # 2) Oude stijl: bekende bool functies
            used = False
            for cand in BOOL_FN_CANDIDATES:
                bf = getattr(mod, cand, None)
                if callable(bf):
                    out[key] = bool(bf(bot_id=bot_id, verbose=verbose))
                    used = True
                    break

            # 3) Extra: pak eerste callable die begint met is_
            if not used:
                for attr in dir(mod):
                    if attr.startswith("is_") and callable(getattr(mod, attr)):
                        out[key] = bool(getattr(mod, attr)(bot_id=bot_id, verbose=verbose))
                        used = True
                        break

            if not used:
                # niks bruikbaars, skip
                pass

        except Exception as e:
            errors[key] = f"{type(e).__name__}: {e}"

    return {"state": out, "errors": errors}
