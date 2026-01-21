import time
from states.collect_statuses import collect_statuses
from telemetry import update_state

def refresh_state(*, bot_id: int, verbose: bool = False):
    res = collect_statuses(bot_id=bot_id, verbose=verbose)
    st = res["state"]

    logged_in = bool(st.get("logged_in"))
    sk_signal = bool(st.get("skilling")) or bool(st.get("skilling_signal"))

    # altijd alles opslaan (watch/debug)
    update_state(
        bot_id,
        state=st,
        errors=res["errors"],
        heartbeat_at=time.time(),
    )

    # gated conclusie (extra veld, breekt niks)
    if logged_in:
        update_state(bot_id, skilling=sk_signal, gate={"skilling_blocked_by": None})
    else:
        update_state(bot_id, skilling=False, gate={"skilling_blocked_by": "logged_out"})
