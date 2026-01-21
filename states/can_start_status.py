import time

from states.should_play_status import should_play
from states.skilling_status import is_skilling
from states.logged_in_status import logged_in

from core.helpers.assist_login import assist_login
from core.helpers.assist_logout import assist_logout


def can_continue(
    *,
    bot_id,
    verbose,
    do_actions=True,
    login_wait_s=1.2,
):
    # 1) toestemming
    if not should_play(bot_id=bot_id, verbose=verbose):
        if do_actions:
            assist_logout(bot_id=bot_id, verbose=verbose)
        verbose and print("🛑 Not allowed to play")
        return False

    # 2) login
    if not logged_in(bot_id=bot_id, verbose=verbose):
        if do_actions:
            verbose and print("🔐 Logging in")
            assist_login(bot_id=bot_id, verbose=verbose)
            time.sleep(float(login_wait_s))
            # re-check zodat je niet infinite login-spam krijgt
            if not logged_in(bot_id=bot_id, verbose=False):
                return False
        else:
            verbose and print("🔴 Not logged in")
        return False

    # 3) skilling check alleen als je ingelogd bent (nu guaranteed)
    if is_skilling(bot_id=bot_id, verbose=verbose):
        verbose and print("🟢 Already skilling")
        return False

    return True
