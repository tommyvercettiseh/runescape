import time
from helpers.log import log

def op_log(verbose, msg, trace=False, debug=False, level="info"):
    if level == "ok":
        if debug:
            log(verbose, msg, trace)
        return
    log(verbose, msg, trace)

def wait_until(fn, timeout=0, interval=1.0):
    t_end = time.time() + float(timeout) if timeout and timeout > 0 else None
    while True:
        out = fn()
        if out:
            return out
        if not timeout or timeout <= 0 or time.time() >= t_end:
            return None
        time.sleep(float(interval))
