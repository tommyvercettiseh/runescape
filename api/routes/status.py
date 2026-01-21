from __future__ import annotations

import time
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query

from telemetry import read_state, update_state

router = APIRouter()

BOT_IDS = (1, 2, 3, 4)

API_KEY = "bullshit"
REQUIRE_KEY = False  # later True zetten

# Als True: runtime_s wordt ook in je state_bot_X.json weggeschreven
PERSIST_RUNTIME = True

def _iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _auth(key: str):
    if not REQUIRE_KEY:
        return
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

def _norm_status(s: dict) -> str:
    # voorkeur: ui_status
    ui = (s.get("ui_status") or "").lower().strip()
    if ui in {"running", "done", "fail", "stopped"}:
        return ui

    active = bool(s.get("active"))
    if active:
        return "running"

    rc = s.get("last_rc")
    if rc == 0:
        return "done"
    if isinstance(rc, int) and rc != 0:
        return "fail"
    return "unknown"

def _calc_runtime_s(s: dict, now: float) -> int:
    started = s.get("started_at")
    ended = s.get("ended_at")
    active = bool(s.get("active"))
    status = _norm_status(s)

    if isinstance(started, (int, float)):
        if active or status == "running":
            return max(0, int(now - float(started)))
        if isinstance(ended, (int, float)):
            return max(0, int(float(ended) - float(started)))
        # niet actief maar geen ended_at → neem updated_at moment als "einde"
        return max(0, int(now - float(started)))
    return 0

def _augment_bot_state(bot_id: int, s: dict) -> dict:
    now = time.time()
    out = dict(s)

    status = _norm_status(out)
    runtime_s = _calc_runtime_s(out, now)

    out["status"] = status
    out["runtime_s"] = runtime_s  # voor de watch super handig
    out["server_ts"] = now

    # optioneel: stale detectie
    hb = out.get("heartbeat_at")
    if isinstance(hb, (int, float)):
        out["heartbeat_age_s"] = max(0, int(now - float(hb)))

    # terugschrijven naar json (zoals jij wilt)
    if PERSIST_RUNTIME:
        update_state(bot_id, status=status, runtime_s=runtime_s)

    return out

def _bundle() -> dict:
    data = {"updated_at": _iso(), "bots": {}}
    latest = None

    for b in BOT_IDS:
        s = read_state(b)
        out = _augment_bot_state(b, s)
        data["bots"][str(b)] = out

        ts = out.get("updated_at")
        if ts and (latest is None or ts > latest):
            latest = ts

    if latest:
        data["updated_at"] = latest

    return data

@router.get("/health")
def health():
    return {"ok": True, "ts": _iso()}

@router.get("/status")
def status(x_api_key: str = Query(default="")):
    _auth(x_api_key)
    return _bundle()

@router.get("/status_public")
def status_public(key: str = Query(default="")):
    # browser friendly
    _auth(key)
    return _bundle()

@router.get("/status/{bot_id}")
def status_one(bot_id: int, key: str = Query(default="")):
    _auth(key)
    if bot_id not in BOT_IDS:
        raise HTTPException(status_code=404, detail="unknown bot_id")
    s = read_state(bot_id)
    return _augment_bot_state(bot_id, s)
