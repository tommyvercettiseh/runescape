from __future__ import annotations

import json
import os
from pathlib import Path


def safe_read_json(path: Path):
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def safe_write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def ensure_debug_meta_exists(meta_file: Path, debug_meta_file: Path):
    if debug_meta_file.exists():
        return
    if meta_file.exists():
        safe_write_json(debug_meta_file, safe_read_json(meta_file))
    else:
        safe_write_json(debug_meta_file, {})


def load_all_metadata(meta_file: Path, debug_meta_file: Path):
    if debug_meta_file.exists():
        return safe_read_json(debug_meta_file)
    return safe_read_json(meta_file)


def save_template_metadata(meta_file: Path, debug_meta_file: Path, template_name: str, settings_dict: dict):
    main_dict = dict(settings_dict)
    main_dict.pop("area", None)

    meta_main = safe_read_json(meta_file)
    meta_main[template_name] = main_dict
    safe_write_json(meta_file, meta_main)

    meta_dbg = safe_read_json(debug_meta_file)
    meta_dbg[template_name] = settings_dict
    safe_write_json(debug_meta_file, meta_dbg)


def delete_template_metadata(meta_file: Path, debug_meta_file: Path, template_name: str):
    meta_main = safe_read_json(meta_file)
    if template_name in meta_main:
        meta_main.pop(template_name, None)
        safe_write_json(meta_file, meta_main)

    meta_dbg = safe_read_json(debug_meta_file)
    if template_name in meta_dbg:
        meta_dbg.pop(template_name, None)
        safe_write_json(debug_meta_file, meta_dbg)