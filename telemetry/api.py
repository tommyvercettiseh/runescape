from __future__ import annotations
from typing import Any, Dict

from telemetry.state_io import update_state as _update_state, read_state as _read_state

def update_state(bot_id: int, **kwargs) -> Dict[str, Any]:
    return _update_state(bot_id, kwargs)

def set_state(bot_id: int, key: str, value: Any) -> Dict[str, Any]:
    return _update_state(bot_id, {key: value})

def read_state(bot_id: int) -> Dict[str, Any]:
    return _read_state(bot_id)
