from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from telemetry.paths import STATE_DIR, state_path

def _iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst

def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def update_state(bot_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = state_path(bot_id)

    current = read_json(path)

    patch = dict(patch)
    patch.setdefault("bot_id", bot_id)
    patch["updated_at"] = _iso_utc()

    merged = _deep_merge(current, patch)
    write_json(path, merged)
    return merged

def read_state(bot_id: int) -> Dict[str, Any]:
    data = read_json(state_path(bot_id))
    if not data:
        return {
            "bot_id": bot_id,
            "updated_at": _iso_utc(),
            "active": False,
            "ui_status": "unknown",
        }
    return data
