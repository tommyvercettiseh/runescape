import sys
from core.config import load_json

# 🆔 Offset matrix per bot (exact zoals je vorige bot)
BOT_OFFSETS = {
    1: (0, 0),
    2: (958, 0),
    3: (0, 498),
    4: (958, 498),
}

def get_bot_id(default=1):
    try:
        return int(sys.argv[1])
    except (IndexError, ValueError):
        return default

def get_offset(bot_id):
    return BOT_OFFSETS.get(int(bot_id), (0, 0))

def load_areas(filename="areas.json"):
    raw = load_json(filename, required=True)

    # categorie-structuur
    if isinstance(raw, dict) and raw and all(isinstance(v, dict) for v in raw.values()):
        flat = {}
        for _category, subdict in raw.items():
            for name, coords in subdict.items():
                flat[name] = coords
        return flat

    # flat structuur
    if isinstance(raw, dict) and (not raw or all(isinstance(v, list) for v in raw.values())):
        return raw

    raise ValueError("areas.json structuur onbekend.")

def apply_offset(coords, bot_id):
    ox, oy = get_offset(bot_id)
    x1, y1, x2, y2 = coords
    return [x1 + ox, y1 + oy, x2 + ox, y2 + oy]
