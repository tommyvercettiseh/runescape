from __future__ import annotations

import importlib
import pkgutil
import random
import time

_LAST_TS = {}  # (bot_id, event_id) -> ts


def _cooldown_ok(bot_id, event_id, cooldown_s):
    now = time.time()
    key = (bot_id, event_id)
    last = _LAST_TS.get(key, 0.0)
    if now - last >= float(cooldown_s):
        _LAST_TS[key] = now
        return True
    return False


def _discover_events(pkg_name="helpers.random_events"):
    """
    Auto vindt alle modules event_*.py in helpers/random_events/
    Verwacht per module: EVENT = {"id": str, "chance": float, "cooldown_s": float, "run": callable}
    """
    events = []
    pkg = importlib.import_module(pkg_name)

    for m in pkgutil.iter_modules(pkg.__path__):
        if not m.name.startswith("event_"):
            continue

        mod = importlib.import_module(f"{pkg_name}.{m.name}")
        ev = getattr(mod, "EVENT", None)

        if isinstance(ev, dict) and callable(ev.get("run")) and ev.get("id"):
            events.append(ev)

    return events


def assist_random_event(
    *,
    bot_id=1,
    area="Bot_Area",
    base_chance=0.07,
    verbose=True,
    package="helpers.random_events",
):
    """
    Roept af en toe random een event aan (plugin-style).
    Return True als er een event uitgevoerd is.
    """
    if random.random() > float(base_chance):
        return False

    events = _discover_events(package)
    if not events:
        if verbose:
            print("🎲 random_event: geen events gevonden")
        return False

    ev = random.choice(events)

    ev_id = str(ev.get("id", "unknown"))
    ev_chance = float(ev.get("chance", 1.0))
    cooldown_s = float(ev.get("cooldown_s", 20))

    if random.random() > ev_chance:
        return False

    if not _cooldown_ok(bot_id, ev_id, cooldown_s):
        return False

    if verbose:
        print(f"🎲 random_event: {ev_id} (cooldown {cooldown_s}s)")

    ev["run"](bot_id=bot_id, area=area, verbose=verbose)
    return True
