from __future__ import annotations
import json
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]  # pas aan als jouw structuur anders is
STATE_DIR = ROOT / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

def _state_path(bot_id: int) -> Path:
    return STATE_DIR / f"return_guard_bot_{bot_id}.json"

def _load(bot_id: int) -> Dict:
    p = _state_path(bot_id)
    if not p.exists():
        return {"consecutive_returns": 0}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"consecutive_returns": 0}

def _save(bot_id: int, data: Dict) -> None:
    _state_path(bot_id).write_text(json.dumps(data, indent=2), encoding="utf-8")

def record_return(bot_id: int) -> int:
    data = _load(bot_id)
    data["consecutive_returns"] = int(data.get("consecutive_returns", 0)) + 1
    _save(bot_id, data)
    return data["consecutive_returns"]

def reset_returns(bot_id: int) -> None:
    data = _load(bot_id)
    data["consecutive_returns"] = 0
    _save(bot_id, data)

def hit_max_returns(bot_id: int, max_returns: int) -> bool:
    data = _load(bot_id)
    return int(data.get("consecutive_returns", 0)) >= int(max_returns)
