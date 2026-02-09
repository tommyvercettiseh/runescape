from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BATTERY_DIR = ROOT / "telemetry" / "battery"


def _iso_local() -> str:
    # Local time is fine here; this is a human-facing "per day" budget.
    return datetime.now().isoformat(timespec="seconds")


def _today_local() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _date_of_ts_local(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def _next_midnight_local_ts(ts: float) -> float:
    dt = datetime.fromtimestamp(ts)
    nm = (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return nm.timestamp()


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _battery_path(bot_id: int, date_str: str | None = None) -> Path:
    date_str = date_str or _today_local()
    return BATTERY_DIR / f"battery_bot{int(bot_id)}_{date_str}.json"


def _open_path(bot_id: int) -> Path:
    return BATTERY_DIR / f"open_bot{int(bot_id)}.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic-ish write: write to temp file in same dir, then replace.
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{time.time_ns()}")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _compute_fatigue(used_sec: float, budget_sec: float) -> tuple[float | None, float | None]:
    used_sec = max(0.0, float(used_sec))
    budget_sec = float(budget_sec)
    if budget_sec <= 0:
        return None, None
    fatigue = _clamp(used_sec / budget_sec, 0.0, 1.0)
    battery = _clamp(1.0 - fatigue, 0.0, 1.0)
    return fatigue, battery


def get_day_status(bot_id: int, *, budget_sec: float) -> dict[str, Any]:
    """
    Read today's battery file (if present) and return a normalized status.
    Does not create files.
    """
    path = _battery_path(bot_id)
    data = _read_json(path)
    used = float(data.get("used_sec", 0.0) or 0.0)
    fatigue, battery = _compute_fatigue(used, float(budget_sec))
    return {
        "bot_id": int(bot_id),
        "date": _today_local(),
        "budget_sec": float(budget_sec),
        "used_sec": used,
        "fatigue": fatigue,
        "battery": battery,
        "path": str(path),
    }


def _update_day_file(
    bot_id: int,
    date_str: str,
    *,
    add_sec: float,
    budget_sec: float,
    session: dict[str, Any] | None,
) -> dict[str, Any]:
    path = _battery_path(bot_id, date_str)
    cur = _read_json(path)

    used = float(cur.get("used_sec", 0.0) or 0.0)
    used += max(0.0, float(add_sec))

    fatigue, battery = _compute_fatigue(used, float(budget_sec))

    payload: dict[str, Any] = {
        "date": date_str,
        "bot_id": int(bot_id),
        "budget_sec": float(budget_sec),
        "used_sec": round(used, 6),
        "fatigue": fatigue,
        "battery": battery,
        "updated_at": _iso_local(),
    }

    # Keep history if present
    sessions = cur.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    if session:
        sessions.append(session)
    payload["sessions"] = sessions

    _write_json(path, payload)
    return payload


def _split_by_local_day(start_ts: float, end_ts: float) -> list[tuple[str, float, float]]:
    """
    Returns list of (date_str, part_start_ts, part_end_ts) in local time.
    """
    out: list[tuple[str, float, float]] = []
    t = float(start_ts)
    end_ts = float(end_ts)
    while t < end_ts:
        date_str = _date_of_ts_local(t)
        midnight = _next_midnight_local_ts(t)
        part_end = end_ts if end_ts < midnight else midnight
        out.append((date_str, t, part_end))
        t = part_end
    return out


def begin_session(
    bot_id: int,
    *,
    started_at: float,
    budget_sec: float,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Persist an "open session" marker per bot.
    If an older open session exists, it is auto-closed at this start time (recovery).
    """
    started_at = float(started_at)
    budget_sec = float(budget_sec)
    open_path = _open_path(bot_id)

    prev = _read_json(open_path)
    prev_start = prev.get("started_at")
    if isinstance(prev_start, (int, float)) and float(prev_start) < started_at:
        # Close previous at this start time to prevent stuck sessions.
        end_session(
            bot_id,
            ended_at=started_at,
            reason="recovered_overlap",
            meta={"recovered": True},
        )

    payload: dict[str, Any] = {
        "bot_id": int(bot_id),
        "started_at": started_at,
        "budget_sec": budget_sec,
        "meta": meta or {},
        "updated_at": _iso_local(),
    }
    _write_json(open_path, payload)
    return payload


def end_session(
    bot_id: int,
    *,
    ended_at: float,
    reason: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Close an open session (if any) and add its runtime to the per-day battery files.
    Returns the last updated day payload (or None if nothing to close).
    """
    open_path = _open_path(bot_id)
    cur = _read_json(open_path)
    start_ts = cur.get("started_at")
    budget_sec = cur.get("budget_sec", 0.0)

    if not isinstance(start_ts, (int, float)):
        return None

    start_ts = float(start_ts)
    ended_at = float(ended_at)
    if ended_at <= start_ts:
        try:
            open_path.unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass
        return None

    last_payload = None
    parts = _split_by_local_day(start_ts, ended_at)

    for date_str, p_start, p_end in parts:
        sec = max(0.0, p_end - p_start)
        session = {
            "start_ts": round(float(p_start), 6),
            "end_ts": round(float(p_end), 6),
            "sec": round(float(sec), 6),
            "reason": str(reason),
            "meta": meta or {},
        }
        last_payload = _update_day_file(
            bot_id,
            date_str,
            add_sec=sec,
            budget_sec=float(budget_sec),
            session=session,
        )

    try:
        open_path.unlink(missing_ok=True)  # type: ignore[arg-type]
    except Exception:
        pass

    return last_payload
