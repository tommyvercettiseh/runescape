import inspect
from pathlib import Path


def trace(enabled, depth=0, skip_parts=("helpers",)):
    if not enabled:
        return ""

    stack = inspect.stack()

    # skip interne frames (helpers, log wrappers, etc.)
    for f in stack[1:]:
        p = Path(f.filename)
        parts = p.parts
        if any(sp in parts for sp in skip_parts):
            continue
        return f" | {p.name}:{f.lineno}::{f.function}"

    # fallback (als alles skipped)
    f = stack[min(len(stack) - 1, max(1, depth))]
    p = Path(f.filename)
    return f" | {p.name}:{f.lineno}::{f.function}"
