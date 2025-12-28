"""
commit.py

Doel
Snelle, veilige git commits maken zonder steeds alle commands te typen.

Wat het doet
1 toont git status
2 vraagt om commit message
3 voert git add + git commit uit
"""

import subprocess
import sys


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

    message = input("✍️  Commit message: ").strip()
    if not message:
        print("❌ Commit message is verplicht.")
        return

    run_git_command(["git", "add", "."])
    run_git_command(["git", "commit", "-m", message])

    print("✅ Commit gemaakt!")

push = input("🚀 Push naar GitHub? (y/n): ").lower().strip()
if push == "y":
    run_git_command(["git", "push"])
    print("🌍 Gepusht naar GitHub")

if __name__ == "__main__":
    main()
