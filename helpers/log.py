ANSI = True

def _c(code):
    return f"\x1b[{code}m" if ANSI else ""

RESET = _c("0")
GREEN = _c("32")
RED = _c("31")
YELLOW = _c("33")
CYAN = _c("36")

def log(verbose, msg, trace=False, depth=0):
    if not verbose:
        return
    print(msg)