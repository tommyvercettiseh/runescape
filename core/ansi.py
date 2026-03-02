from __future__ import annotations
import os

# ============================================================
# Windows ANSI fix
# ============================================================
if os.name == "nt":
    try:
        import colorama
        colorama.init()
    except Exception:
        pass


# ============================================================
# Case-insensitive dict + attribute compat
# ============================================================
class _AnsiDict(dict):

    def _normalize(self, key):
        return key.lower() if isinstance(key, str) else key

    def __getitem__(self, key):
        return super().__getitem__(self._normalize(key))

    def get(self, key, default=None):
        return super().get(self._normalize(key), default)

    def __contains__(self, key):
        return super().__contains__(self._normalize(key))

    # ✅ Backwards compat: ANSI.GREEN / ANSI.RESET etc
    # ✅ Also compat: ANSI.fail("x") / ANSI.ok("x") etc (forward to ANSIx)
    def __getattr__(self, name):
        key = name.lower()

        # ANSI.GREEN / ANSI.RESET / ANSI.PURPLE etc
        if key in self:
            return self[key]

        # ANSI.fail("..") / ANSI.ok("..") / ANSI.warn("..") etc
        forward = {
            "wrap",
            "ok", "fail", "warn", "info",
            "goed", "fout",
            "ja_nee", "aan_uit", "gevonden",
        }
        if key in forward:
            return getattr(ANSIx, key)

        raise AttributeError(f"'_AnsiDict' object has no attribute '{name}'")


# ============================================================
# Base colour values (één keer gedefinieerd)
# ============================================================
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"

_RED    = "\033[91m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_BLUE   = "\033[94m"
_PURPLE = "\033[95m"
_CYAN   = "\033[96m"
_GRAY   = "\033[90m"
_ORANGE = "\033[38;5;208m"


# ============================================================
# ANSI dictionary (EN + NL aliases)
# ============================================================
ANSI = _AnsiDict({

    # base
    "reset": _RESET,
    "bold": _BOLD,
    "dim": _DIM,

    # EN colours
    "red": _RED,
    "green": _GREEN,
    "yellow": _YELLOW,
    "blue": _BLUE,
    "purple": _PURPLE,
    "cyan": _CYAN,
    "gray": _GRAY,
    "orange": _ORANGE,

    # NL aliases
    "rood": _RED,
    "groen": _GREEN,
    "geel": _YELLOW,
    "blauw": _BLUE,
    "paars": _PURPLE,
    "cyaan": _CYAN,
    "grijs": _GRAY,
    "oranje": _ORANGE,

    # theme aliases
    "area": _PURPLE,
})


# ============================================================
# Optional helper API (mooier gebruik)
# ============================================================
class ANSIx:

    @staticmethod
    def wrap(text: str, colour_key: str) -> str:
        c = ANSI.get(colour_key)
        return f"{c}{text}{ANSI['reset']}" if c else text

    # Status
    @staticmethod
    def ok(text: str) -> str:
        return ANSIx.wrap(text, "green")

    @staticmethod
    def fail(text: str) -> str:
        return ANSIx.wrap(text, "red")

    @staticmethod
    def warn(text: str) -> str:
        return ANSIx.wrap(text, "yellow")

    @staticmethod
    def info(text: str) -> str:
        return ANSIx.wrap(text, "cyan")

    # NL status
    @staticmethod
    def goed(text: str) -> str:
        return ANSIx.ok(text)

    @staticmethod
    def fout(text: str) -> str:
        return ANSIx.fail(text)

    @staticmethod
    def ja_nee(value: bool) -> str:
        return ANSIx.ok("Ja") if value else ANSIx.fail("Nee")

    @staticmethod
    def aan_uit(value: bool) -> str:
        return ANSIx.ok("Aan") if value else ANSIx.fail("Uit")

    @staticmethod
    def gevonden(value: bool) -> str:
        return ANSIx.ok("Gevonden") if value else ANSIx.fail("Niet gevonden")