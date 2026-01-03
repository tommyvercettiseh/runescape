# Copilot instructions for this repository

This file gives concise, actionable guidance for AI coding agents working in this repository.

## Purpose
- Repository contains small automation and vision helpers for a RuneScape botting toolset: core platform code (`core/`), vision utilities (`vision/`), tools and scripts (`tools/`, `scripts/`), and test helpers (`modules/`, `core/test_test.py`).

## Big-picture architecture
- `core/`: primary runtime logic and helpers (e.g. `core/ai_cursor.py`, `core/click_image.py`, `core/config.py`). Prefer editing code here when implementing runtime behavior.
- `vision/`: image processing and recognition (`vision/image_recognition.py`, `vision/image_detection.py`, `vision/move_to_image.py`). This is where detection algorithms live.
- `config/` and `assets/`: JSON-driven data (areas, templates) used at runtime (`config/areas.json`, `assets/areas/*`). Changes here are data-driven, not code changes.
- `tools/` and `scripts/`: developer utilities and one-off scripts. Many scripts include a small bootstrap that inserts project root into `sys.path` — preserve that when modifying scripts.

## Key patterns & conventions
- Scripts often start with a bootstrap that inserts the repo root into `sys.path` (see top of `speedrun.py`). Run scripts from repo root or keep that bootstrap when changing import behavior.
- Config objects use frozen `dataclass` types (see `CursorMotionConfig` in `speedrun.py`). Follow this pattern for small config blocks.
- Motion/cursor utilities record artifacts (e.g. `CursorRecorder` in `speedrun.py`) — many scripts intentionally persist logs/artifacts. Preserve save behavior unless intentionally changing UX.
- There are duplicate/archived copies: `ai_cursor.py` exists at repo root, `core/ai_cursor.py`, and `archive/ai_cursor.py`. Edit `core/ai_cursor.py` for runtime behavior; avoid editing `archive/` or stray duplicates unless refactoring intentionally.

## Running & testing
- Run quick scripts directly from the repo root. Examples:

```
python speedrun.py
python scripts/first_script.py
```

- Tests are colocated in `modules/` and `core/` (simple pytest style). Use `pytest` from the repo root to run tests.

```
pip install pytest pynput pyautogui
pytest -q
```

If `requirements.txt` is missing, install the runtime deps discovered in imports: `pyautogui`, `pynput`, and common test deps like `pytest`.

## Where to make changes
- Feature/runtime behavior: update `core/` files.
- Vision/detection: update `vision/` files and test with images in `assets/images/`.
- Data changes: update `config/` or `assets/` JSON files.
- Small developer utilities: update `tools/` or `scripts/`.

## Integration points
- Template and presets: `core/template_presets_store.py` and `config/templates_meta.json` are used to persist detection templates.
- Area/config JSONs: `config/areas.json` and `assets/areas/*` feed location data to pathing and area helpers in `core/paths.py` and `core/move_to_area.py`.

## Style & safety notes for the agent
- Preserve existing public APIs and file locations; the repo relies on small script-level imports.
- Avoid changing bootstrapping import logic unless converting the repository to a package (this is non-trivial and out-of-scope for small edits).
- Respect archived copies in `archive/` — they are historical and should not be changed.

## Useful files to inspect when triaging issues
- `core/ai_cursor.py`, `core/click_image.py`, `vision/image_recognition.py`, `speedrun.py`, `config/areas.json`, `assets/areas/`, `tools/area_debugger.py`.

---
If anything here is unclear or you'd like more detail on a specific subsystem (vision, cursor motion, or area data), tell me which area to expand and I'll update this file.
