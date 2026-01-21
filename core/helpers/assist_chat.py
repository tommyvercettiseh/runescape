from __future__ import annotations

import json
import random
from pathlib import Path
from core.chat_scheduler import Schedule, can_fire, mark_fired
from ai_keyboard import type_text, press_enter  # <-- pas aan naar jouw echte functienamen
from ai_keyboard import type_text, press_key

def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _load_state(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"used_line_ids": []}


def _save_state(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def assist_chat(
    *,
    bot_id=1,
    file="config/chat/dialogue_test.json",
    min_interval_s=420,
    jitter_s=60,
    from_h=9,
    to_h=22,
    open_chat=True,
    send=True,
    verbose=True,
) -> bool:
    root = Path(__file__).resolve().parents[2]  # Runescape/
    dialogue_path = root / file

    state_dir = root / "runtime" / "chat_state"
    used_file = state_dir / f"{dialogue_path.stem}.used.json"
    throttle_file = state_dir / f"{dialogue_path.stem}.throttle.json"

    schedule = Schedule(
        min_interval_s=min_interval_s,
        jitter_s=jitter_s,
        active_from_h=from_h,
        active_to_h=to_h,
    )

    if not can_fire(throttle_file, schedule):
        return False

    data = _load_json(dialogue_path)
    lines = data.get("lines", [])

    state = _load_state(used_file)
    used = set(state.get("used_line_ids", []))

    # alleen lines die deze bot mag zeggen
    candidates = [
        ln for ln in lines
        if int(ln.get("from", -1)) == int(bot_id)
        and str(ln.get("id", "")) not in used
    ]

    if not candidates:
        if verbose:
            print(f"💬 assist_chat: geen nieuwe lines meer voor bot {bot_id}")
        mark_fired(throttle_file)
        return False

    line = random.choice(candidates)
    line_id = str(line["id"])
    text = str(line["text"])

    if verbose:
        print(f"💬 Bot{bot_id} zegt: {text}")

    if open_chat:
        press_enter()
    type_text(text)
    if send:
        press_enter()


    used.add(line_id)
    state["used_line_ids"] = sorted(used)
    _save_state(used_file, state)

    mark_fired(throttle_file)
    return True
