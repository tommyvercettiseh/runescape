from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class HubPaths:
    repo_root: Path
    mouse_lab: Path
    recordings: Path
    master_profile: Path
    runtime_profile: Path
    state_file: Path
    logs: Path
    profile_history: Path

    @classmethod
    def discover(cls) -> "HubPaths":
        repo_root = Path(__file__).resolve().parents[2]
        mouse_lab = repo_root / "tools" / "mouse_lab"
        recordings = mouse_lab / "recordings"
        hub_data = repo_root / "data" / "mouse_profile_hub"
        logs = hub_data / "logs"
        history = hub_data / "profile_history"
        for folder in (recordings, hub_data, logs, history):
            folder.mkdir(parents=True, exist_ok=True)
        return cls(
            repo_root=repo_root,
            mouse_lab=mouse_lab,
            recordings=recordings,
            master_profile=recordings / "master_profile.json",
            runtime_profile=repo_root / "master_profile.json",
            state_file=hub_data / "session_state.json",
            logs=logs,
            profile_history=history,
        )


@dataclass(frozen=True)
class SessionInfo:
    session_id: str
    folder: Path
    modified_at: datetime
    label: str
    mode: str
    duration_seconds: float
    duration_text: str
    profile_preview: Path | None
    points_file: Path | None
    included: bool = True
    event_count: int = 0
    quality: str = "Unknown"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def load_session_state(path: Path) -> dict[str, dict[str, Any]]:
    raw = _read_json(path)
    sessions = raw.get("sessions") if isinstance(raw, dict) else None
    return sessions if isinstance(sessions, dict) else {}


def save_session_state(path: Path, state: dict[str, dict[str, Any]]) -> None:
    _atomic_write_json(path, {"schema_version": 1, "sessions": state})


def set_session_included(path: Path, session_id: str, included: bool) -> None:
    state = load_session_state(path)
    current = state.get(session_id, {})
    state[session_id] = {**current, "included": bool(included)}
    save_session_state(path, state)


def set_session_label(path: Path, session_id: str, label: str) -> None:
    clean = label.strip() or "Unknown"
    state = load_session_state(path)
    current = state.get(session_id, {})
    state[session_id] = {**current, "label": clean}
    save_session_state(path, state)


def _find_metadata(folder: Path) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for name in ("profile_preview.json", "meta.json", "metadata.json"):
        candidate = folder / name
        if candidate.exists():
            merged.update(_read_json(candidate))
    return merged


def _find_points_file(folder: Path) -> Path | None:
    for name in ("points.csv", "mouse_points.csv", "movement.csv"):
        candidate = folder / name
        if candidate.exists() and candidate.is_file():
            return candidate
    candidates = sorted(folder.glob("*points*.csv"))
    return candidates[0] if candidates else None


def _parse_float(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def load_points(path: Path | None, max_points: int = 5000) -> list[tuple[float, float, float]]:
    if path is None or not path.exists():
        return []
    points: list[tuple[float, float, float]] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error):
        return []
    if not rows:
        return []

    header = [cell.strip().lower() for cell in rows[0]]
    has_header = any(name in header for name in ("x", "mouse_x", "timestamp", "ts", "time"))
    data_rows = rows[1:] if has_header else rows

    def column(names: Sequence[str], fallback: int) -> int:
        for name in names:
            if name in header:
                return header.index(name)
        return fallback

    t_idx = column(("timestamp", "ts", "time", "t"), 0)
    x_idx = column(("x", "mouse_x", "cursor_x"), 1)
    y_idx = column(("y", "mouse_y", "cursor_y"), 2)
    stride = max(1, len(data_rows) // max_points)
    for row in data_rows[::stride]:
        if max(t_idx, x_idx, y_idx) >= len(row):
            continue
        t = _parse_float(row[t_idx])
        x = _parse_float(row[x_idx])
        y = _parse_float(row[y_idx])
        if t is None or x is None or y is None:
            continue
        points.append((t, x, y))
    return points


def _duration_from_points(points: Sequence[tuple[float, float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    duration = points[-1][0] - points[0][0]
    if duration > 100_000:
        duration /= 1000.0
    return max(0.0, duration)


def _format_duration(value: Any) -> str:
    seconds = _parse_float(value)
    if seconds is None:
        return "—"
    seconds_i = max(0, int(seconds))
    hours, remainder = divmod(seconds_i, 3600)
    minutes, seconds_i = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds_i:02d}"


def discover_sessions(recordings_dir: Path, state_file: Path | None = None) -> list[SessionInfo]:
    if not recordings_dir.exists():
        return []
    state = load_session_state(state_file) if state_file else {}
    preview_paths = sorted(
        (p for p in recordings_dir.rglob("profile_preview.json") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    sessions: list[SessionInfo] = []
    seen: set[Path] = set()
    for preview in preview_paths:
        folder = preview.parent
        if folder in seen:
            continue
        seen.add(folder)
        meta = _find_metadata(folder)
        points_file = _find_points_file(folder)
        points = load_points(points_file, max_points=1000)
        duration = _parse_float(meta.get("duration_s") or meta.get("duration_seconds"))
        if duration is None or duration <= 0:
            duration = _duration_from_points(points)
        session_id = str(folder.relative_to(recordings_dir)).replace("\\", "/")
        override = state.get(session_id, {})
        mode = str(meta.get("mode") or "Unknown")
        label = str(override.get("label") or meta.get("label") or mode).strip().title() or "Unknown"
        included = bool(override.get("included", True))
        quality = "Good" if len(points) >= 25 and preview.stat().st_size > 10 else "Limited"
        sessions.append(
            SessionInfo(
                session_id=session_id,
                folder=folder,
                modified_at=datetime.fromtimestamp(preview.stat().st_mtime),
                label=label,
                mode=mode,
                duration_seconds=float(duration or 0.0),
                duration_text=_format_duration(duration),
                profile_preview=preview,
                points_file=points_file,
                included=included,
                event_count=len(points),
                quality=quality,
            )
        )
    return sessions


def load_master_profile(path: Path) -> dict[str, Any]:
    return _read_json(path) if path.exists() else {}


def _runtime_mapping(master: dict[str, Any]) -> dict[str, Any]:
    nested = ((master.get("ai_cursor_mapping") or {}).get("mouse_profile") or {})
    if not isinstance(nested, dict):
        nested = {}
    allowed = {
        "speed_min", "speed_max", "overshoot_min", "overshoot_max", "pre_click_s",
        "click_hold_s", "settle_s", "close_px", "micro_tremor_max",
    }
    runtime = {key: value for key, value in nested.items() if key in allowed and isinstance(value, (int, float))}
    runtime["profile_version"] = str(master.get("profile_version") or "0.1.0")
    runtime["profile_id"] = str(master.get("profile_id") or "hes_master_profile")
    runtime["source_count"] = len(master.get("sources") or [])
    runtime["generated_at"] = str(master.get("created_local") or datetime.now().isoformat(timespec="seconds"))
    return runtime


def build_master_profile(paths: HubPaths, sessions: Iterable[SessionInfo]) -> dict[str, Any]:
    selected = [s for s in sessions if s.included and s.profile_preview and s.profile_preview.exists()]
    if not selected:
        raise ValueError("Geen geldige, ingeschakelde recordings gevonden.")
    from tools.mouse_lab.build_master_profile import build_master

    master = build_master([s.profile_preview for s in selected if s.profile_preview is not None])
    master["profile_version"] = "0.1.0"
    master["selected_session_ids"] = [s.session_id for s in selected]
    master["labels"] = sorted({s.label for s in selected})
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_path = paths.profile_history / f"master_profile_{stamp}.json"
    _atomic_write_json(history_path, master)
    _atomic_write_json(paths.master_profile, master)
    _atomic_write_json(paths.runtime_profile, _runtime_mapping(master))
    return master


def start_mouse_lab(paths: HubPaths, label: str) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["MOUSE_LAB_LABEL"] = label.strip().upper() or "NORMAL"
    log_path = paths.logs / f"mouse_lab_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_handle = log_path.open("a", encoding="utf-8")
    try:
        return subprocess.Popen(
            [sys.executable, "-m", "tools.mouse_lab.mouse_lab"],
            cwd=paths.repo_root,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception:
        log_handle.close()
        raise


def stop_process(process: subprocess.Popen[str] | None, timeout: float = 3.0) -> bool:
    if process is None or process.poll() is not None:
        return True
    process.terminate()
    try:
        process.wait(timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout)
        return True


def normalize_path(points: Sequence[tuple[float, float, float]], count: int = 64) -> list[tuple[float, float]]:
    if len(points) < 2:
        return []
    xy = [(p[1], p[2]) for p in points]
    cumulative = [0.0]
    for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
        cumulative.append(cumulative[-1] + math.hypot(x2 - x1, y2 - y1))
    total = cumulative[-1]
    if total <= 0:
        return []
    result: list[tuple[float, float]] = []
    cursor = 0
    for i in range(count):
        target = total * i / max(1, count - 1)
        while cursor + 1 < len(cumulative) and cumulative[cursor + 1] < target:
            cursor += 1
        nxt = min(cursor + 1, len(xy) - 1)
        span = cumulative[nxt] - cumulative[cursor]
        ratio = 0.0 if span <= 0 else (target - cumulative[cursor]) / span
        x = xy[cursor][0] + (xy[nxt][0] - xy[cursor][0]) * ratio
        y = xy[cursor][1] + (xy[nxt][1] - xy[cursor][1]) * ratio
        result.append((x, y))
    min_x, max_x = min(x for x, _ in result), max(x for x, _ in result)
    min_y, max_y = min(y for _, y in result), max(y for _, y in result)
    width, height = max(1.0, max_x - min_x), max(1.0, max_y - min_y)
    return [((x - min_x) / width, (y - min_y) / height) for x, y in result]


def generate_profile_replay(real_path: Sequence[tuple[float, float]], master: dict[str, Any]) -> list[tuple[float, float]]:
    if not real_path:
        return []
    globals_stats = master.get("globals") or {}
    overshoot = _parse_float((globals_stats.get("overshoot_px") or {}).get("p50")) or 0.0
    curvature = _parse_float((globals_stats.get("curv_p90") or {}).get("p50")) or 0.0
    strength = min(0.035, 0.008 + overshoot / 2500.0 + abs(curvature) / 200.0)
    output: list[tuple[float, float]] = []
    for index, (x, y) in enumerate(real_path):
        t = index / max(1, len(real_path) - 1)
        wave = math.sin(t * math.pi) * math.sin(t * math.pi * 2.0)
        nx = min(1.0, max(0.0, x + wave * strength * 0.45))
        ny = min(1.0, max(0.0, y + wave * strength))
        output.append((nx, ny))
    output[0] = real_path[0]
    output[-1] = real_path[-1]
    return output


def similarity_score(left: Sequence[tuple[float, float]], right: Sequence[tuple[float, float]]) -> float | None:
    if not left or not right or len(left) != len(right):
        return None
    rms = math.sqrt(sum((ax - bx) ** 2 + (ay - by) ** 2 for (ax, ay), (bx, by) in zip(left, right)) / len(left))
    return round(max(0.0, min(100.0, 100.0 * (1.0 - rms / math.sqrt(2.0)))), 1)
