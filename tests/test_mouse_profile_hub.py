from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.mouse_profile_hub.services import (
    HubPaths,
    build_master_profile,
    discover_sessions,
    generate_profile_replay,
    load_master_profile,
    load_points,
    normalize_path,
    set_session_included,
    similarity_score,
)


def _write_session(root: Path, name: str = "gaming/run1", duration: int = 1458) -> Path:
    session = root / name
    session.mkdir(parents=True)
    (session / "profile_preview.json").write_text(
        json.dumps(
            {
                "mode": "gaming",
                "label": "Gaming",
                "duration_s": duration,
                "globals": {
                    "median_speed_px_s": {"n": 10, "p10": 700, "p50": 900, "p90": 1400},
                    "overshoot_px": {"n": 10, "p10": 1, "p50": 5, "p90": 12},
                    "pre_click_ms": {"n": 10, "p10": 40, "p50": 80, "p90": 120},
                    "click_hold_ms": {"n": 10, "p10": 20, "p50": 35, "p90": 60},
                    "tail_time_ms": {"n": 10, "p10": 40, "p50": 80, "p90": 140},
                    "stop_time_ms": {"n": 10, "p10": 20, "p50": 40, "p90": 80},
                },
                "by_phase": {},
            }
        ),
        encoding="utf-8",
    )
    with (session / "points.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "x", "y"])
        for i in range(100):
            writer.writerow([i * 0.01, i * 3, 100 + i])
    return session


def test_discover_sessions_reads_profile_and_points(tmp_path: Path):
    session = _write_session(tmp_path)
    sessions = discover_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0].label == "Gaming"
    assert sessions[0].duration_text == "00:24:18"
    assert sessions[0].points_file == session / "points.csv"
    assert sessions[0].event_count == 100
    assert sessions[0].quality == "Good"


def test_session_inclusion_persists(tmp_path: Path):
    _write_session(tmp_path)
    state = tmp_path / "state.json"
    session = discover_sessions(tmp_path, state)[0]
    set_session_included(state, session.session_id, False)
    refreshed = discover_sessions(tmp_path, state)[0]
    assert refreshed.included is False


def test_invalid_json_is_safe(tmp_path: Path):
    session = tmp_path / "broken"
    session.mkdir()
    (session / "profile_preview.json").write_text("not-json", encoding="utf-8")
    sessions = discover_sessions(tmp_path)
    assert len(sessions) == 1
    assert sessions[0].label == "Unknown"
    assert sessions[0].quality == "Limited"


def test_load_points_and_normalize(tmp_path: Path):
    session = _write_session(tmp_path)
    points = load_points(session / "points.csv")
    normalized = normalize_path(points, count=32)
    assert len(points) == 100
    assert len(normalized) == 32
    assert normalized[0][0] == 0.0
    assert normalized[-1][0] == 1.0


def test_similarity_is_data_driven():
    path = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]
    assert similarity_score(path, path) == 100.0
    changed = [(0.0, 0.0), (0.5, 0.7), (1.0, 1.0)]
    assert 0 < similarity_score(path, changed) < 100


def test_profile_replay_preserves_endpoints():
    real = [(0.0, 0.5), (0.5, 0.2), (1.0, 0.5)]
    replay = generate_profile_replay(real, {"globals": {}})
    assert replay[0] == real[0]
    assert replay[-1] == real[-1]
    assert len(replay) == len(real)


def test_build_master_exports_runtime_profile(tmp_path: Path):
    recordings = tmp_path / "tools" / "mouse_lab" / "recordings"
    _write_session(recordings)
    data = tmp_path / "data" / "mouse_profile_hub"
    paths = HubPaths(
        repo_root=tmp_path,
        mouse_lab=tmp_path / "tools" / "mouse_lab",
        recordings=recordings,
        master_profile=recordings / "master_profile.json",
        runtime_profile=tmp_path / "master_profile.json",
        state_file=data / "session_state.json",
        logs=data / "logs",
        profile_history=data / "profile_history",
    )
    paths.profile_history.mkdir(parents=True)
    sessions = discover_sessions(recordings)
    master = build_master_profile(paths, sessions)
    runtime = load_master_profile(paths.runtime_profile)
    assert master["profile_version"] == "0.1.0"
    assert runtime["profile_id"] == "hes_master_profile"
    assert runtime["source_count"] == 1
    assert runtime["speed_min"] > 0


def test_load_master_profile_missing_is_empty(tmp_path: Path):
    assert load_master_profile(tmp_path / "missing.json") == {}
