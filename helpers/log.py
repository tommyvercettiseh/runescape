from helpers.trace import trace as _trace


def log(verbose, msg, trace=False, depth=3):
    if not verbose:
        return
    print(f"{msg}{_trace(trace, depth=depth)}")

def _log_not_found(image_name, area_name, trace=False, trace_depth=5, elapsed=None, **_):
    # elapsed en extra kwargs zijn optioneel, zodat detect_image nooit crasht op logging
    if elapsed is None:
        msg = f"❌ Not found: {image_name} in {area_name}"
    else:
        msg = f"❌ Not found: {image_name} in {area_name} | {elapsed:.2f}s"

    # jouw bestaande log/trace hier laten staan
    # bijv:
    # log(True, msg, trace=trace, depth=trace_depth)
    print(msg) if trace else None
