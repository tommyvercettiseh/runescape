from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HubPaths:
    repo_root: Path
    mouse_lab: Path
    recordings: Path
    master_profile: Path

    @classmethod
    def discover(cls) -> "HubPaths":
        repo_root = Path(__file__).resolve().parents[2]
        mouse_lab = repo_root / "tools" / "mouse_lab"
        recordings = mouse_lab / "recordings"
        recordings.mkdir(parents=True, exist_ok=True)
        return cls(
            repo_root=repo_root,
            mouse_lab=mouse_lab,
            recordings=recordings,
            master_profile=recordings / "master_profile.json",
        )


@dataclass(frozen=True)
class SessionInfo:
    session_id: str
    folder: Path
    modified_at: datetime
    label: str
    mode: str
    duration_text: str
    profile_preview: Path | None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _find_metadata(folder: Path) -> dict[str, Any]:
    for name in ("metadata.json", "meta.json", "profile_preview.json"):
        path = folder / name
        if path.exists():
            data = _read_json(path)
            if data:
                return data
    return {}


def discover_sessions(recordings_dir: Path) -> list[SessionInfo]:
    sessions: list[SessionInfo] = []
    if not recordings_dir.exists():
        return sessions

    preview_paths = sorted(
        recordings_dir.rglob("profile_preview.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    seen: set[Path] = set()
    for preview in preview_paths:
        folder = preview.parent
        if folder in seen:
            continue
        seen.add(folder)
        meta = _find_metadata(folder)
        modified = datetime.fromtimestamp(preview.stat().st_mtime)
        mode = str(meta.get("mode") or "Unknown")
        label = str(meta.get("label") or mode).title()
        duration = meta.get("duration_s") or meta.get("duration_seconds")
        duration_text = _format_duration(duration)
        sessions.append(
            SessionInfo(
                session_id=folder.name,
                folder=folder,
                modified_at=modified,
                label=label,
                mode=mode,
                duration_text=duration_text,
                profile_preview=preview,
            )
        )
    return sessions


def _format_duration(value: Any) -> str:
    try:
        seconds = max(0, int(float(value)))
    except (TypeError, ValueError):
        return "—"
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def load_master_profile(path: Path) -> dict[str, Any]:
    return _read_json(path) if path.exists() else {}


def rebuild_master_profile(paths: HubPaths, latest_runs: int | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(paths.mouse_lab / "build_master_profile.py")]
    if latest_runs is not None:
        command.extend(["--n", str(max(1, latest_runs))])
    return subprocess.run(
        command,
        cwd=paths.repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def start_mouse_lab(paths: HubPaths) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-m", "tools.mouse_lab.mouse_lab"],
        cwd=paths.repo_root,
        text=True,
    )
