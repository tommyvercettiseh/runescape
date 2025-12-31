from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

BOT_OFFSETS: Dict[int, Tuple[int, int]] = {
    1: (0, 0),
    2: (958, 0),
    3: (0, 498),
    4: (958, 498),
}

Coords = List[int]
AreasDict = Dict[str, Coords]

ROOT = Path(__file__).resolve().parents[1]
AREAS_ROOT = ROOT / "assets" / "areas"
DEFAULT_PACK = "skills/skills.json"

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

def get_bot_id(default: int = 1) -> int:
    try:
        return int(sys.argv[1])
    except (IndexError, ValueError):
        return default

def get_offset(bot_id: int) -> Tuple[int, int]:
    return BOT_OFFSETS.get(int(bot_id), (0, 0))

def apply_offset(coords: Any, bot_id: int) -> Coords:
    ox, oy = get_offset(bot_id)
    x1, y1, x2, y2 = _normalize_coords(coords)
    return [x1 + ox, y1 + oy, x2 + ox, y2 + oy]

def _list_packs() -> List[str]:
    if not AREAS_ROOT.exists():
        return []
    packs = sorted([p for p in AREAS_ROOT.glob("**/*.json") if p.is_file()])
    return [str(p.relative_to(AREAS_ROOT)).replace("\\", "/") for p in packs]

def _pick_default_pack() -> str:
    packs = _list_packs()
    if not packs:
        fallback = AREAS_ROOT / "skills" / "skills.json"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        if not fallback.exists():
            fallback.write_text("{}", encoding="utf-8")
        return "skills/skills.json"

    if DEFAULT_PACK in packs:
        return DEFAULT_PACK
    if "skills/skills.json" in packs:
        return "skills/skills.json"
    return packs[0]

def _load_json_file(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Areas pack niet gevonden: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Areas pack JSON kapot: {path} -> {e}") from e

def load_areas(pack: str | None = None) -> AreasDict:
    pack = (pack or "").replace("\\", "/").strip() or _pick_default_pack()
    path = (AREAS_ROOT / pack).resolve()

    raw = _load_json_file(path)
    if not isinstance(raw, dict):
        raise ValueError(f"Areas pack structuur onbekend (verwacht dict): {path}")

    if raw and all(isinstance(v, dict) for v in raw.values()):
        flat: AreasDict = {}
        for _category, subdict in raw.items():
            if not isinstance(subdict, dict):
                continue
            for name, coords in subdict.items():
                flat[str(name)] = _normalize_coords(coords)
        return flat

    out: AreasDict = {}
    for name, coords in raw.items():
        out[str(name)] = _normalize_coords(coords)
    return out
