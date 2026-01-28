from __future__ import annotations

"""Project-wide autoload.

Doel:
  1 import en je hebt assist_*, state functies en vision helpers direct beschikbaar.

Gebruik in scripts (na je bootstrap):

    from core.autoload import autoload
    autoload(globals())

Daarna kun je gewoon:
    assist_login(...)
    detect_image(...)
    should_play(...)
"""

from core.main_loader import LoadSpec, load_exports


_CACHE: dict[str, object] | None = None


def _build_exports(*, verbose=False):
    exports: dict[str, object] = {}

    # =========================
    # AUTO EXPORT SPECS
    # =========================
    specs = [
        # ✅ STATES: laadt automatisch alles uit states/*.py
        LoadSpec(
            package="states",
            public_only=True,
            export_constants=False,
        ),

        # ✅ Helpers: assist_* modules + assist_* functies
        LoadSpec(
            package="core.helpers",
            module_prefix="assist_",
            name_prefix="assist_",
            public_only=True,
            export_constants=False,
            exclude_modules={
                "assist_testing",
            },
        ),

        # ✅ Helpers: functies die NIET met assist_ beginnen (maar wel in assist_* modules zitten)
        # Voorbeeld: inventory_full (in assist_inventory_full.py)
        LoadSpec(
            package="core.helpers",
            module_prefix="assist_",
            only_names={
                "inventory_full",
            },
            public_only=True,
            export_constants=False,
            exclude_modules={
                "assist_testing",
            },
        ),

        # ✅ Vision: alleen de API die jij wil
        LoadSpec(
            package="vision",
            public_only=True,
            export_constants=False,
            exclude_modules={"image_recognition"},
            only_names={
                "detect_image",
                "detect_images",
                "detect_color",
                "detect_colours",
                "find_color",
                "find_colours",
                "match_template",
                "match_templates",
            },
        ),

        # ✅ Helpers (algemene project helpers)
        LoadSpec(
            package="helpers",
            only_names={
                "sleep_custom",
                "random_sleep",
                "random_sleep_range",
            },
            public_only=True,
            export_constants=False,
        ),

        # ✅ Core: veelgebruikte tools (whitelist om conflicts te voorkomen)
        LoadSpec(
            package="core",
            only_names={
                "click_image",
                "move_in_area",
                "random_mouse_movement",
                "move_and_click",
                "get_offset",
                "apply_offset",
                "drop_inventory",  # ✅ vaak nodig
            },
            public_only=True,
            export_constants=False,
            exclude_modules={
                "api",
                "autoload",
                "main_loader",
                "bootstrap",
            },
        ),
    ]

    loaded, _origins = load_exports(specs, verbose=verbose, fail_on_dupes=True)
    exports.update(loaded)

    # =========================================================
    # ROOT MODULES (losse .py in project root, bv ai_keyboard.py)
    # =========================================================
    try:
        import importlib

        kb = importlib.import_module("ai_keyboard")  # ai_keyboard.py in ROOT
        if hasattr(kb, "press_key"):
            exports["press_key"] = kb.press_key
    except Exception:
        pass

    return exports


def get_exports(*, verbose=False) -> dict[str, object]:
    global _CACHE
    if _CACHE is None:
        _CACHE = _build_exports(verbose=verbose)
    return _CACHE


def autoload(namespace: dict, *, verbose=False) -> dict[str, object]:
    """Injecteert alle exports in jouw script namespace.

    Tip:
      autoload(globals())
    """
    exports = get_exports(verbose=verbose)
    namespace.update(exports)
    return exports
