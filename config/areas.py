from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # pas aan indien nodig
AREAS_FILE = PROJECT_ROOT / "config" / "areas.json"

# cache: slug(key) -> real_key
_AREA_INDEX: Optional[Dict[str, str]] = None


# ============================================================
# MODEL
# ============================================================

@dataclass(frozen=True)
class Area:
    key: str
    path: Path
    value: Any


# ============================================================
# INTERNALS
# ============================================================

def _slug(s: str) -> str:
    return str(s).strip().lower().replace(" ", "").replace("_", "").replace("-", "")

def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        return {}

    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _normalize(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Support:
    1) Nieuw: {"Name": {"coords":[..],"group":"bank"}}
    2) Oud:  {"Name": [x1,y1,x2,y2]}  -> wordt {"coords":[..],"group":"default"}
    """
    out: Dict[str, Dict[str, Any]] = {}

    for name, v in (data or {}).items():
        if isinstance(v, list) and len(v) == 4:
            out[name] = {"coords": v, "group": "default"}
            continue

        if isinstance(v, dict):
            coords = v.get("coords")
            if isinstance(coords, list) and len(coords) == 4:
                out[name] = {"coords": coords, "group": (v.get("group") or "default")}
                continue

    return out


# ============================================================
# PUBLIC API
# ============================================================

def build_area_index(areas_file: Union[str, Path] = AREAS_FILE, *, use_cache: bool = True) -> Dict[str, str]:
    global _AREA_INDEX

    if use_cache and _AREA_INDEX is not None:
        return _AREA_INDEX

    fp = Path(areas_file).expanduser().resolve()
    data = _normalize(_read_json(fp))

    idx: Dict[str, str] = {}
    for real_key in data.keys():
        idx.setdefault(_slug(real_key), real_key)

    if use_cache:
        _AREA_INDEX = idx

    return idx


def load_area(area_key: str, areas_file: Union[str, Path] = AREAS_FILE) -> Area:
    fp = Path(areas_file).expanduser().resolve()
    idx = build_area_index(fp, use_cache=True)

    want = _slug(area_key)
    if want not in idx:
        sample = ", ".join(sorted(idx.values())[:12]) or "(geen keys gevonden)"
        raise FileNotFoundError(f"❌ Area key niet gevonden: {area_key}\n🔎 Voorbeelden: {sample}")

    real_key = idx[want]
    data = _normalize(_read_json(fp))

    if real_key not in data:
        raise ValueError(f"❌ Key stond in index maar niet meer in file: {real_key} ({fp})")

    return Area(key=real_key, path=fp, value=data[real_key])


def load_coords(area_key: str, areas_file: Union[str, Path] = AREAS_FILE) -> Tuple[int, int, int, int]:
    a = load_area(area_key, areas_file)
    c = a.value.get("coords")
    if not (isinstance(c, list) and len(c) == 4):
        raise ValueError(f"❌ Area heeft geen geldige coords: {a.key}")
    return int(c[0]), int(c[1]), int(c[2]), int(c[3])


def load_group(group: str, areas_file: Union[str, Path] = AREAS_FILE) -> Dict[str, Tuple[int, int, int, int]]:
    fp = Path(areas_file).expanduser().resolve()
    data = _normalize(_read_json(fp))
    g = (group or "").strip().lower()

    out: Dict[str, Tuple[int, int, int, int]] = {}
    for name, obj in data.items():
        if (obj.get("group") or "default").strip().lower() != g:
            continue
        c = obj.get("coords")
        if isinstance(c, list) and len(c) == 4:
            out[name] = (int(c[0]), int(c[1]), int(c[2]), int(c[3]))
    return out


def clear_area_cache() -> None:
    global _AREA_INDEX
    _AREA_INDEX = None


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    print("AREAS_FILE =", AREAS_FILE)
    print("keys =", list(build_area_index().values())[:10])
    # voorbeeld:
    # print(load_area("Bank_Deposit"))
    # print(load_coords("Bank_Deposit"))
    # print(load_group("bank"))
