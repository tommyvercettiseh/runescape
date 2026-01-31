from __future__ import annotations

import importlib
import importlib.util
import pkgutil
from dataclasses import dataclass


@dataclass(frozen=True)
class LoadSpec:
    package: str
    module_prefix: str | None = None
    name_prefix: str | None = None
    only_names: set[str] | None = None
    exclude_names: set[str] | None = None
    public_only: bool = True
    exclude_modules: set[str] | None = None
    export_constants: bool = True


def _iter_module_fullnames(package: str):
    spec = importlib.util.find_spec(package)
    if spec is None:
        return

    pkg_path = getattr(spec, "submodule_search_locations", None)
    if not pkg_path:
        return

    for m in pkgutil.iter_modules(pkg_path, package + "."):
        full_name = m.name
        short_name = full_name.split(".")[-1]

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
    exports: dict[str, object] = {}
    origins: dict[str, str] = {}

    for spec in specs:
        for full_name, short_name in _iter_module_fullnames(spec.package) or []:
            if spec.module_prefix and not short_name.startswith(spec.module_prefix):
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
                is_simple_const = isinstance(obj, (int, float, str, dict, list, set, tuple))

                if callable(obj):
                    if getattr(obj, "__module__", None) != mod.__name__:
                        continue
                else:
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
