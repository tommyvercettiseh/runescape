from __future__ import annotations

from pathlib import Path
import argparse
import shutil

ROOT = Path(__file__).resolve().parent

REPLACEMENTS = {
    "states.can_start_status": "states.status_can_start",
    "from states.can_start_status import": "from states.status_can_start import",
    "can_start(": "status_can_start(",
}

BACKUP_SUFFIX = ".bak"


def iter_py_files(root: Path):
    for p in root.rglob("*.py"):
        # skip backups / venv / cache
        if p.name.endswith(".py.bak"):
            continue
        if any(part in ("venv", ".venv", "__pycache__", ".git") for part in p.parts):
            continue
        yield p


def apply_replacements(text: str):
    new_text = text
    for old, new in REPLACEMENTS.items():
        new_text = new_text.replace(old, new)
    return new_text


def dry_run():
    hits = 0
    files = 0

    for path in iter_py_files(ROOT):
        text = path.read_text(encoding="utf-8")
        new_text = apply_replacements(text)

        if new_text != text:
            files += 1
            diff_count = 0
            for old, new in REPLACEMENTS.items():
                c = text.count(old)
                if c:
                    diff_count += c
                    hits += c
            print(f"👀 {path}  ({diff_count} hits)")

    print(f"\n✅ Dry-run klaar: {files} bestanden zouden veranderen, totaal {hits} replacements.")


def apply():
    changed = 0
    hits_total = 0

    for path in iter_py_files(ROOT):
        text = path.read_text(encoding="utf-8")
        new_text = apply_replacements(text)

        if new_text != text:
            # backup
            backup = path.with_suffix(path.suffix + BACKUP_SUFFIX)
            if not backup.exists():
                shutil.copy(path, backup)

            # count hits
            hits = 0
            for old in REPLACEMENTS.keys():
                hits += text.count(old)

            path.write_text(new_text, encoding="utf-8")
            print(f"✏️  aangepast: {path}  ({hits} hits)")
            changed += 1
            hits_total += hits

    print(f"\n✅ Apply klaar: {changed} bestanden aangepast, totaal {hits_total} replacements.")
    print("↩️  Undo kan met: python refactor_tool.py undo")


def undo():
    restored = 0
    for bak in ROOT.rglob("*.py.bak"):
        if any(part in ("venv", ".venv", "__pycache__", ".git") for part in bak.parts):
            continue

        original = bak.with_suffix("")  # .py.bak -> .py
        shutil.move(bak, original)
        print(f"↩️  hersteld: {original}")
        restored += 1

    print(f"\n✅ Undo klaar: {restored} bestanden teruggedraaid.")


def main():
    parser = argparse.ArgumentParser(description="Project-wide refactor replace tool (dry/apply/undo).")
    parser.add_argument("mode", choices=("dry", "apply", "undo"), help="dry=preview, apply=change+backup, undo=restore backups")
    args = parser.parse_args()

    if args.mode == "dry":
        dry_run()
    elif args.mode == "apply":
        apply()
    elif args.mode == "undo":
        undo()


if __name__ == "__main__":
    main()
