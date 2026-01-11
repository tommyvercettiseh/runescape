from __future__ import annotations

import os
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# 🆔 Offset matrix per bot (fallback / backwards compat)
BOT_OFFSETS: Dict[int, Tuple[int, int]] = {
    1: (0, 0),
    2: (958, 0),
    3: (0, 498),
    4: (958, 498),
}

Coords = List[int]            # [x1, y1, x2, y2]
AreasDict = Dict[str, Coords] # {"Info Area": [..], ...}

# ============================================================
# ===== START AREAS SOURCE (NU: ALLEEN config/areas.json) =====
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
AREAS_FILE = (ROOT / "config" / "areas.json").resolve()

CONFIG_PACK = "config/areas.json"
DEFAULT_PACK = CONFIG_PACK
# ============================================================
# ===== END AREAS SOURCE =====================================
# ============================================================

_OFFSETS_JSON_CACHE: Dict[int, Tuple[int, int]] | None = None


def _to_int(v: Any) -> int:
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip().replace(",", ".")
        return int(float(s))
    return int(v)


def _normalize_coords(coords: Any) -> Coords:
    if not (isinstance(coords, list) and len(coords) == 4):
        raise ValueError(f"Area coords moeten [x1,y1,x2,y2] zijn, kreeg: {coords!r}")

    x1, y1, x2, y2 = (_to_int(coords[0]), _to_int(coords[1]), _to_int(coords[2]), _to_int(coords[3]))

    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1

    return [x1, y1, x2, y2]


def _load_offsets_json() -> Dict[int, Tuple[int, int]]:
    global _OFFSETS_JSON_CACHE
    if _OFFSETS_JSON_CACHE is not None:
        return _OFFSETS_JSON_CACHE

    path = (ROOT / "offsets.json").resolve()
    if not path.exists():
        _OFFSETS_JSON_CACHE = {}
        return _OFFSETS_JSON_CACHE

    try:
        raw = path.read_text(encoding="utf-8-sig")  # ✅ BOM-proof
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        _OFFSETS_JSON_CACHE = {}
        return _OFFSETS_JSON_CACHE

    out: Dict[int, Tuple[int, int]] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list) and len(v) == 2:
                try:
                    out[int(k)] = (int(v[0]), int(v[1]))
                except Exception:
                    try:
                        out[int(k)] = (0, 0)
                    except Exception:
                        pass

    _OFFSETS_JSON_CACHE = out
    return _OFFSETS_JSON_CACHE


def get_bot_id(default: int = 1) -> int:
    # 1) runner faked argv: script.py <bot_id>
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1])
        except Exception:
            pass

    # 2) manager env fallback
    try:
        return int(os.getenv("BOT_ID", str(default)))
    except Exception:
        return default


def get_offset(bot_id: int | None = None) -> Tuple[int, int]:
    # ✅ Variant A: get_offset(2)
    # ✅ Variant B: get_offset()

    # 1) manager env override (als je manager dit meegeeft)
    ex = os.getenv("BOT_OFFSET_X")
    ey = os.getenv("BOT_OFFSET_Y")
    if ex is not None and ey is not None:
        try:
            return int(ex), int(ey)
        except Exception:
            pass

    # 2) bot_id bepalen
    if bot_id is None:
        bot_id = get_bot_id()

    # 3) offsets.json voorrang
    offsets_file = _load_offsets_json()
    if offsets_file:
        return offsets_file.get(int(bot_id), (0, 0))

    # 4) fallback hardcoded
    return BOT_OFFSETS.get(int(bot_id), (0, 0))


def apply_offset(coords: Any, bot_id: int | None = None) -> Coords:
    # ✅ Variant A: apply_offset(coords, 2)
    # ✅ Variant B: apply_offset(coords)
    ox, oy = get_offset(bot_id)
    x1, y1, x2, y2 = _normalize_coords(coords)
    return [x1 + ox, y1 + oy, x2 + ox, y2 + oy]


def _ensure_areas_file_exists():
    AREAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not AREAS_FILE.exists():
        AREAS_FILE.write_text("{}", encoding="utf-8")


def _list_packs() -> List[str]:
    _ensure_areas_file_exists()
    return [CONFIG_PACK]


def _pick_default_pack() -> str:
    _ensure_areas_file_exists()
    return CONFIG_PACK


def _pack_to_path(_pack: str) -> Path:
    _ensure_areas_file_exists()
    return AREAS_FILE


def _load_json_file(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Areas file niet gevonden: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Areas JSON kapot: {path} -> {e}") from e


def _flatten_areas(raw: Any, *, verbose: bool = False) -> AreasDict:
    if not isinstance(raw, dict):
        return {}

    if "areas" in raw and isinstance(raw["areas"], dict):
        raw = raw["areas"]

    def extract_coords(v: Any) -> Coords | None:
        if isinstance(v, list) and len(v) == 4:
            return _normalize_coords(v)

        if isinstance(v, dict):
            for k in ("coords", "xyxy", "box", "rect"):
                if k in v and isinstance(v[k], list) and len(v[k]) == 4:
                    return _normalize_coords(v[k])

        return None

    out: AreasDict = {}

    for name, val in raw.items():
        if isinstance(val, dict) and not any(k in val for k in ("coords", "xyxy", "box", "rect")):
            for subname, subval in val.items():
                coords = extract_coords(subval)
                if coords is None:
                    if verbose:
                        print(f"⚠️ skip entry (geen coords): {name}/{subname} = {subval!r}")
                    continue
                out[str(subname)] = coords
            continue

        coords = extract_coords(val)
        if coords is None:
            if verbose:
                print(f"⚠️ skip entry (geen coords): {name} = {val!r}")
            continue

        out[str(name)] = coords

    return out


def load_areas(pack: str | None = None, *, all_packs: bool = False, verbose: bool = False) -> AreasDict:
    _ensure_areas_file_exists()

    if all_packs:
        merged: AreasDict = {}
        seen_from: Dict[str, str] = {}
        packs = _list_packs()

        if verbose:
            print(f"📦 load_areas(all_packs=True) packs gevonden: {len(packs)}")
            print("📍 source file:", str(AREAS_FILE))

        for rel in packs:
            path = _pack_to_path(rel)
            raw = _load_json_file(path)
            flat = _flatten_areas(raw, verbose=verbose)

            for name, coords in flat.items():
                if name in merged:
                    if verbose:
                        print(f"⚠️ duplicate area '{name}' in {rel} (al in {seen_from[name]}) -> skip")
                    continue
                merged[name] = coords
                seen_from[name] = rel

        if verbose:
            print(f"✅ merged areas: {len(merged)}")
            print("🧩 sample keys:", list(merged.keys())[:10])

        return merged

    pack = (pack or "").replace("\\", "/").strip() or _pick_default_pack()
    path = _pack_to_path(pack)

    raw = _load_json_file(path)
    flat = _flatten_areas(raw, verbose=verbose)

    if verbose:
        print("📦 load_areas pack:", pack)
        print("📄 load_areas path:", str(path.resolve()))
        print("✅ areas loaded:", len(flat))
        print("🧩 sample keys:", list(flat.keys())[:10])

    return flat
