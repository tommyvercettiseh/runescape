# ================================
# META FILES (MAIN + DEBUGGER)
# ================================
META_MAIN = Path(CONFIG_DIR) / "templates_meta.json"
META_DEBUG = Path(CONFIG_DIR) / "templates_meta_debugger.json"

def ensure_debugger_meta_exists():
    if META_DEBUG.exists():
        return
    if not META_MAIN.exists():
        _safe_write_json(META_DEBUG, {})
        return
    _safe_write_json(META_DEBUG, _safe_read_json(META_MAIN))


def load_all_metadata():
    return _safe_read_json(META_DEBUG) if META_DEBUG.exists() else _safe_read_json(META_MAIN)


def save_template_metadata(template_name, settings_dict):
    main_dict = dict(settings_dict)
    main_dict.pop("area", None)

    meta_main = _safe_read_json(META_MAIN)
    meta_main[template_name] = main_dict
    _safe_write_json(META_MAIN, meta_main)

    meta_dbg = _safe_read_json(META_DEBUG)
    meta_dbg[template_name] = settings_dict
    _safe_write_json(META_DEBUG, meta_dbg)


def delete_template_metadata(template_name):
    meta_main = _safe_read_json(META_MAIN)
    if template_name in meta_main:
        meta_main.pop(template_name, None)
        _safe_write_json(META_MAIN, meta_main)

    meta_dbg = _safe_read_json(META_DEBUG)
    if template_name in meta_dbg:
        meta_dbg.pop(template_name, None)
        _safe_write_json(META_DEBUG, meta_dbg)
