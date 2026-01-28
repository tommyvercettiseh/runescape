from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass


@dataclass(frozen=True)
class LoadSpec:
    """Wat moet er geladen worden uit een package."""

    package: str

    # Alleen modules laden die hier mee beginnen, bv "assist_"
    module_prefix: str | None = None

    # Alleen exports die hier mee beginnen, bv "assist_"
    name_prefix: str | None = None

    # Alleen exports in deze whitelist (als gezet)
    only_names: set[str] | None = None

    # Sluit deze namen uit
    exclude_names: set[str] | None = None

    # Exporteer geen dingen die met '_' beginnen
    public_only: bool = True

    # Skip deze modules (op basis van short module name)
    exclude_modules: set[str] | None = None

    # ✅ Nieuw: exporteer simpele constants (dict/str/int/...) of niet
    # Zet deze op False voor packages zoals vision (ANSI clashes).
    export_constants: bool = True


def _iter_module_fullnames(package: str):
    pkg = importlib.import_module(package)

    # Namespace packages hebben soms geen __path__
    pkg_path = getattr(pkg, "__path__", None)
    if not pkg_path:
        return

    for m in pkgutil.iter_modules(pkg_path, pkg.__name__ + "."):
        full_name = m.name
        short_name = full_name.split(".")[-1]

        # skip rommel zoals "assist_ - kopie" (geen geldig module id)
        if not short_name.isidentifier():
            continue

        yield full_name, short_name


def load_exports(
    specs: list[LoadSpec],
    *,
    verbose=False,
    fail_on_dupes=True,
    skip_import_errors=True,
):
    """Laadt exports volgens specs.

    Returns:
        exports: dict[str, callable|object]
        origins: dict[str, str] (waar komt export vandaan)
    """
    exports: dict[str, object] = {}
    origins: dict[str, str] = {}

    for spec in specs:
        for full_name, short_name in _iter_module_fullnames(spec.package) or []:
            if spec.module_prefix and not short_name.startswith(spec.module_prefix):
                continue

            # ✅ skip kapotte / lege module names zoals assist_.py of assist__.py
            if spec.module_prefix and short_name.startswith(spec.module_prefix):
                rest = short_name[len(spec.module_prefix):]
                if not rest or rest.strip("_") == "":
                    if verbose:
                        print(f"⏭️ skip empty module name: {short_name}")
                    continue

            if spec.exclude_modules is not None and short_name in spec.exclude_modules:
                continue

            try:
                mod = importlib.import_module(full_name)
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                if verbose:
                    print(f"❌ import fail {full_name}: {type(e).__name__}: {e}")
                if skip_import_errors:
                    continue
                raise

            for attr in dir(mod):
                if spec.public_only and attr.startswith("_"):
                    continue

                if spec.name_prefix and not attr.startswith(spec.name_prefix):
                    continue

                if spec.only_names is not None and attr not in spec.only_names:
                    continue

                if spec.exclude_names is not None and attr in spec.exclude_names:
                    continue

                obj = getattr(mod, attr)

                # simpele constants die we evt willen exporteren
                is_simple_const = isinstance(obj, (int, float, str, dict, list, set, tuple))

                if callable(obj):
                    # ✅ Cruciaal: exporteer alleen functions die in deze module zelf gedefinieerd zijn
                    # voorkomt duplicates door "from ... import ..." re-exports
                    if getattr(obj, "__module__", None) != mod.__name__:
                        continue
                else:
                    # ✅ constants alleen exporteren als spec dit toestaat
                    if not spec.export_constants:
                        continue
                    if not is_simple_const:
                        continue

                if attr in exports:
                    msg = f"Duplicate export '{attr}' uit {full_name} (al uit {origins[attr]})"
                    if fail_on_dupes:
                        raise RuntimeError(msg)
                    if verbose:
                        print("⚠️", msg)
                    continue

                exports[attr] = obj
                origins[attr] = full_name

            if verbose:
                print(f"✅ loaded {short_name}")

    return exports, origins
