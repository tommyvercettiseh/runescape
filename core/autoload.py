from __future__ import annotations

import importlib
import os
from pathlib import Path

from core.main_loader import LoadSpec, load_exports  # :contentReference[oaicite:2]{index=2}

_CACHE: dict[str, object] | None = None
_CACHE_KEY: tuple | None = None

# Optioneel: alias mapping blijft handig
ALIASES: dict[str, tuple[str, ...]] = {
    "assist_click_exclude": ("assist_click_exclude", "assist_exclude_bot", "assist_click_exclude_bot"),
}


def _apply_aliases(exports: dict[str, object], *, verbose=False) -> None:
    for alias, candidates in ALIASES.items():
        if alias in exports:
            continue
        for name in candidates:
            if name in exports:
                exports[alias] = exports[name]
                if verbose:
                    print(f"🔁 autoload alias: {alias} → {name}")
                break


def _pkg_fingerprint(packages: list[str]) -> tuple:
    """
    Bouw een key op basis van:
    • alle module-bestanden die in de packages zitten
    • hun mtime (laatste wijziging)
    Hierdoor refresht autoload automatisch als jij iets toevoegt of wijzigt.
    """
    parts: list[tuple[str, float]] = []

    for pkg in packages:
        try:
            mod = importlib.import_module(pkg)
        except Exception:
            continue

        pkg_paths = getattr(mod, "__path__", None)
        if not pkg_paths:
            continue

        for p in pkg_paths:
            base = Path(p)
            if not base.exists():
                continue

            # scan .py files (1 level diep is genoeg voor jouw structuur)
            for f in base.rglob("*.py"):
                try:
                    parts.append((str(f), f.stat().st_mtime))
                except Exception:
                    pass

    parts.sort()
    return tuple(parts)


def _build_exports(*, verbose=False) -> dict[str, object]:
    # 👇 dit is de echte power move: core.helpers zonder assist_ filters
    specs = [
        LoadSpec(package="states", public_only=True, export_constants=False),

        LoadSpec(
            package="core.helpers",
            public_only=True,
            export_constants=False,
            exclude_modules={"assist_testing"},
        ),

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

        LoadSpec(
            package="helpers",
            only_names={"sleep_custom", "random_sleep", "random_sleep_range"},
            public_only=True,
            export_constants=False,
        ),

        LoadSpec(
            package="core",
            only_names={
                "click_image",
                "move_in_area",
                "random_mouse_movement",
                "move_and_click",
                "get_offset",
                "apply_offset",
                "drop_inventory",
            },
            public_only=True,
            export_constants=False,
            exclude_modules={"api", "autoload", "main_loader", "bootstrap"},
        ),
    ]

    loaded, _origins = load_exports(specs, verbose=verbose, fail_on_dupes=True, skip_import_errors=True)
    exports = dict(loaded)

    _apply_aliases(exports, verbose=verbose)

    if verbose:
        # checkjes die jij tof vindt 😄
        for name in ("assist_click_exclude", "assist_exclude_bot", "assist_click_exclude_bot"):
            print(f"🧠 autoload check: {name} {'✅' if name in exports else '❌'}")
        print(f"🧠 autoload check: game_on_button {'✅' if 'game_on_button' in exports else '❌'}")

    return exports


def get_exports(*, verbose=False) -> dict[str, object]:
    global _CACHE, _CACHE_KEY

    # packages waar jij vaak “nieuwe dingen” toevoegt
    key = _pkg_fingerprint(["core.helpers", "states", "helpers", "core", "vision"])

    if _CACHE is None or _CACHE_KEY != key:
        _CACHE_KEY = key
        _CACHE = _build_exports(verbose=verbose)

        if verbose:
            print("♻️ autoload: refreshed (changes detected)")

    return _CACHE


def autoload(namespace: dict, *, verbose=False, force_reload=False) -> dict[str, object]:
    global _CACHE, _CACHE_KEY

    if force_reload:
        _CACHE = None
        _CACHE_KEY = None
        if verbose:
            print("♻️ autoload: force reload")

    exports = get_exports(verbose=verbose)
    namespace.update(exports)
    return exports
