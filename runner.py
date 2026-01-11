from __future__ import annotations

import os
import sys
import runpy
from pathlib import Path

def main():
    # runner.py <script_path> <bot_id>
    if len(sys.argv) < 3:
        print("Gebruik: runner.py <script_path> <bot_id>")
        raise SystemExit(2)

    script_path = Path(sys.argv[1]).resolve()
    bot_id = str(sys.argv[2])

    project_root = Path(__file__).resolve().parent

    # 1) imports fixen: alsof je vanaf project root runt
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # 2) jouw scripts NIET aanpassen: geef bot_id alsof script direct gestart is
    sys.argv = [str(script_path), bot_id]

    # 3) extra: ook env var zetten (kan handig zijn voor andere helpers)
    os.environ["BOT_ID"] = bot_id
    os.environ["PYTHONUTF8"] = "1"

    # 4) run exact script als __main__
    runpy.run_path(str(script_path), run_name="__main__")

if __name__ == "__main__":
    main()
