from __future__ import annotations
import json
from pathlib import Path

LOGS = Path("logs")


def read_jsonl(p: Path):
    items = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def newest(pattern: str) -> Path | None:
    files = sorted(LOGS.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def main():
    if not LOGS.exists():
        print("❌ missing folder:", LOGS)
        return

    bot_path = newest("bot_*.jsonl")
    hw_path  = newest("hw_*.jsonl")

    if not bot_path:
        print("❌ Geen bot_*.jsonl gevonden in logs/")
        return
    if not hw_path:
        print("❌ Geen hw_*.jsonl gevonden in logs/")
        return

    print("BOT:", bot_path.as_posix())
    print("HW :", hw_path.as_posix())
    print()

    bot = read_jsonl(bot_path)
    hw = read_jsonl(hw_path)

    bot.sort(key=lambda x: x["t"])
    hw.sort(key=lambda x: x["t"])

    bot_moves = [e for e in bot if e.get("type") == "move"]
    bot_clicks = [e for e in bot if e.get("type") == "click"]

    hw_moves = [e for e in hw if e.get("type") == "move"]
    hw_clicks = [e for e in hw if e.get("type") == "click" and e.get("pressed") is True]

    print("=== Counts ===")
    print("bot moves :", len(bot_moves))
    print("bot clicks:", len(bot_clicks))
    print("hw moves  :", len(hw_moves))
    print("hw clicks :", len(hw_clicks))
    print()

    n = min(len(bot_clicks), len(hw_clicks))
    if n == 0:
        print("Geen clicks om te matchen.")
        return

    print("=== Click latency (op volgorde) ===")
    deltas = []
    for i in range(n):
        bc = bot_clicks[i]
        hc = hw_clicks[i]
        dt_ms = (hc["t"] - bc["t"]) * 1000.0
        deltas.append(dt_ms)
        print(f"{i+1:02d} bot@{bc['t']:.6f}  hw@{hc['t']:.6f}  Δ={dt_ms:+.1f} ms")

    avg = sum(deltas) / len(deltas)
    p95 = sorted(deltas)[int(0.95 * (len(deltas) - 1))]
    print()
    print(f"avg Δ = {avg:.1f} ms")
    print(f"p95 Δ = {p95:.1f} ms")

    if len(bot_clicks) != len(hw_clicks):
        print()
        print("⚠️ Let op: bot/hw click count verschilt.")
        print("Bot clicks:", len(bot_clicks), "HW clicks:", len(hw_clicks))
        if len(bot_clicks) > len(hw_clicks):
            print("HW mist clicks (of hook ziet ze niet).")
        else:
            print("HW heeft extra clicks (waarschijnlijk jij bewoog/klik tijdens test 😄).")


if __name__ == "__main__":
    main()
