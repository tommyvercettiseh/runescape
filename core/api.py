from __future__ import annotations

"""Één import punt voor je hele project.

Gebruik:
    from core.api import assist_login, should_play, detect_image

Of alles:
    from core.api import *
"""

from core.autoload import get_exports


_exports = get_exports(verbose=False)
globals().update(_exports)
__all__ = sorted(_exports.keys())
