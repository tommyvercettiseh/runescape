"""
find_config_files.py

Doel
Zoekt in de échte PROJECT_ROOT naar areas.json en offsets.json.

Belangrijk
Werkt ook als je PowerShell in C:\\Windows\\System32 staat.
"""

from pathlib import Path
import importlib.util


def import_paths_module():
    current_file_path = Path(__file__).resolve()
    paths_file_path = current_file_path.parent / "paths_draft.py"

    spec = importlib.util.spec_from_file_location("paths_draft_module", paths_file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Kan paths_draft.py niet importeren via: {paths_file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


paths_module = import_paths_module()

project_root = Path(paths_module.PROJECT_ROOT).resolve()

print("✅ find_config_files.py location:", Path(__file__).resolve())
print("✅ paths_draft.py location:", Path(paths_module.__file__).resolve())
print("✅ PROJECT_ROOT:", project_root)

targets = {"areas.json": [], "offsets.json": []}

for file_path in project_root.rglob("*.json"):
    if file_path.name in targets:
        targets[file_path.name].append(file_path)

for filename, found_paths in targets.items():
    print(f"\n🔎 {filename} gevonden: {len(found_paths)}")
    for path in found_paths[:20]:
        print("  ", path)
