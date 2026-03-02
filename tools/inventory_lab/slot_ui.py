from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from tools.inventory_lab.slot_scan import scan_slots, load_cfg, save_cfg


def slot_ui(bot_id=1):
    cfg = load_cfg()

    root = tk.Tk()
    root.title("Inventory Lab | Slot UI")

    state = {
        "bot_id": bot_id,
        "empty_bg_pct": float(cfg["empty_bg_pct"]),
        "pad": int(cfg["pad"]),
        "running": True,
        "last_img": None,
        "photo": None,
    }

    top = ttk.Frame(root, padding=8)
    top.grid(row=0, column=0, sticky="nsew")

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    canvas = tk.Canvas(top, width=360, height=300, highlightthickness=0)
    canvas.grid(row=0, column=0, rowspan=8, padx=(0, 10), sticky="nsew")

    top.columnconfigure(0, weight=1)
    top.rowconfigure(0, weight=1)

    lbl = ttk.Label(top, text="filled=? empty=?")
    lbl.grid(row=0, column=1, sticky="w")

    s1 = ttk.Scale(top, from_=0.15, to=0.95, value=state["empty_bg_pct"])
    s1.grid(row=1, column=1, sticky="ew")
    l1 = ttk.Label(top, text=f"empty_bg_pct: {state['empty_bg_pct']:.2f}")
    l1.grid(row=2, column=1, sticky="w")

    s2 = ttk.Scale(top, from_=2, to=18, value=state["pad"])
    s2.grid(row=3, column=1, sticky="ew")
    l2 = ttk.Label(top, text=f"pad: {state['pad']}")
    l2.grid(row=4, column=1, sticky="w")

    btns = ttk.Frame(top)
    btns.grid(row=5, column=1, sticky="ew")

    def on_save():
        cfg2 = load_cfg()
        cfg2["empty_bg_pct"] = float(state["empty_bg_pct"])
        cfg2["pad"] = int(state["pad"])
        save_cfg(cfg2)

    def on_stop():
        state["running"] = False
        root.destroy()

    ttk.Button(btns, text="SAVE", command=on_save).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(btns, text="CLOSE", command=on_stop).grid(row=0, column=1)

    hint = ttk.Label(top, text="Groen = leeg slot\nRood = gevuld slot")
    hint.grid(row=6, column=1, sticky="w")

    def tick():
        if not state["running"]:
            return

        state["empty_bg_pct"] = float(s1.get())
        state["pad"] = int(round(s2.get()))
        l1.config(text=f"empty_bg_pct: {state['empty_bg_pct']:.2f}")
        l2.config(text=f"pad: {state['pad']}")

        r = scan_slots(
            bot_id=state["bot_id"],
            empty_bg_pct=state["empty_bg_pct"],
            pad=state["pad"],
            debug=True,
        )

        pil_img = r["pil_img"]
        slots = r["slots_xyxy_local"]
        empty_set = set(r["empty_slots"])

        w, h = pil_img.size
        canvas.config(width=w, height=h)

        state["photo"] = ImageTk.PhotoImage(pil_img)
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=state["photo"])

        for i, (x0, y0, x1, y1) in enumerate(slots):
            is_empty = i in empty_set
            color = "#00ff00" if is_empty else "#ff0000"
            canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2)
            canvas.create_text(x0 + 10, y0 + 10, text=str(i), fill=color)

        lbl.config(text=f"filled={r['filled_count']} empty={r['empty_count']} total={r['slots_total']}")

        root.after(180, tick)

    tick()
    root.mainloop()


if __name__ == "__main__":
    slot_ui(bot_id=1)

# cd C:\Users\Hesse\Desktop\Runescape
# python -m tools.inventory_lab.slot_ui