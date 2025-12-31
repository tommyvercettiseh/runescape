"""
autocommit.py

Doel
Volledig automatische git commit met datum en tijd.

Wat het doet
1 toont git status
2 git add .
3 git commit met timestamp
4 optioneel git push
"""

import subprocess
import sys
from datetime import datetime


def run_git_command(command: list[str]) -> str:
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        print("❌ Git error:")
        print(result.stderr)
        sys.exit(1)
    return result.stdout


def main() -> None:
    print("📦 Git status:\n")
    status = run_git_command(["git", "status"])
    print(status)

    if "nothing to commit" in status:
        print("ℹ️  Niets om te committen.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"Auto commit {timestamp}"

    run_git_command(["git", "add", "."])
    run_git_command(["git", "commit", "-m", message])

    print(f"✅ Commit gemaakt: {message}")

    push = input("🚀 Push naar GitHub? (y/n): ").lower().strip()
    if push == "y":
        run_git_command(["git", "push"])
        print("🌍 Gepusht naar GitHub")


if __name__ == "__main__":
    main()
