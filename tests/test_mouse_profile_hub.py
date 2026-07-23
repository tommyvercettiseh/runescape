from __future__ import annotations

import json
from pathlib import Path

from tools.mouse_profile_hub.services import discover_sessions, load_master_profile


def test_discover_sessions_reads_profile_preview(tmp_path: Path):
    session = tmp_path / "gaming" / "2026-07-23_194200"
    session.mkdir(parents=True)
    preview = session / "profile_preview.json"
    preview.write_text(
        json.dumps({"mode": "gaming", "label": "Gaming", "duration_s": 1458}),
        encoding="utf-8",
    )

    sessions = discover_sessions(tmp_path)

    assert len(sessions) == 1
    assert sessions[0].label == "Gaming"
    assert sessions[0].duration_text == "00:24:18"
    assert sessions[0].profile_preview == preview


def test_discover_sessions_ignores_invalid_json(tmp_path: Path):
    session = tmp_path / "broken"
    session.mkdir()
    (session / "profile_preview.json").write_text("not-json", encoding="utf-8")

    sessions = discover_sessions(tmp_path)

    assert len(sessions) == 1
    assert sessions[0].label == "Unknown"


def test_load_master_profile_returns_empty_for_missing_file(tmp_path: Path):
    assert load_master_profile(tmp_path / "missing.json") == {}


def test_load_master_profile_reads_dictionary(tmp_path: Path):
    path = tmp_path / "master_profile.json"
    path.write_text(json.dumps({"profile_id": "hes_master_profile"}), encoding="utf-8")

    profile = load_master_profile(path)

    assert profile["profile_id"] == "hes_master_profile"
