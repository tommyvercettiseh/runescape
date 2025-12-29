from __future__ import annotations

import json
import random
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

# ----------------------------
# Bootstrap: project-root in sys.path
# ----------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bot_offsets import get_offset  # noqa: E402


# ----------------------------
# Packs config
# assets/areas/<pack>/<pack>.json  (maar subfolders zijn ook toegestaan)
# ----------------------------
AREAS_ROOT = ROOT / "assets" / "areas"
AREAS_ROOT.mkdir(parents=True, exist_ok=True)

DEFAULT_PACK = "skills/skills.json"  # als deze niet bestaat pakt hij de eerste die hij vindt

HANDLE_SIZE = 8
HANDLE_OFFSET = 6
HANDLE_FILL = "#ffffff"
HANDLE_OUTLINE = "#333333"


class AreaOverlay(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Areas Debugger")
        self.attributes("-topmost", True)
        self.attributes("-fullscreen", True)
        self.attributes("-transparentcolor", "black")
        self.configure(bg="black")

        self.canvas = tk.Canvas(
            self,
            width=self.winfo_screenwidth(),
            height=self.winfo_screenheight(),
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack()

        # Packs
        self.pack_relpath = self._pick_start_pack()
        self.areas = self.load_areas()
        self.visible_areas = set(self.areas.keys())

        # State
        self.selected_area = None
        self.active_handle = None  # 'nw','n','ne','e','se','s','sw','w'
        self.drag_mode = None      # 'move' or 'resize'
        self.offset_x = 0
        self.offset_y = 0

        self.rect_ids = {}
        self.label_ids = {}
        self.handle_ids = {}

        # Bot offsets
        self.bot_id = 1
        self.x_offset, self.y_offset = get_offset(self.bot_id)

        # UI
        self.create_bot_selector()
        self.draw_areas()
        self.create_selection_window()

        # Bindings
        self.canvas.bind("<Button-1>", self.on_mouse_down_left)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag_left)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up_left)
        self.canvas.bind("<Double-Button-1>", self.on_double_click_canvas)
        self.bind("<Escape>", lambda e: self.destroy())

    # ----------------------------
    # Packs
    # ----------------------------
    def _list_packs(self) -> list[str]:
        packs = sorted([p for p in AREAS_ROOT.glob("**/*.json") if p.is_file()])
        return [str(p.relative_to(AREAS_ROOT)).replace("\\", "/") for p in packs]

    def _pick_start_pack(self) -> str:
        packs = self._list_packs()
        if not packs:
            # Maak een default folder+json aan als er nog niks is
            fallback = AREAS_ROOT / "skills" / "skills.json"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            fallback.write_text("{}", encoding="utf-8")
            return "skills/skills.json"

        if DEFAULT_PACK in packs:
            return DEFAULT_PACK

        # Als je oude structuur had: assets/areas/skills/skills.json, pak die graag
        if "skills/skills.json" in packs:
            return "skills/skills.json"

        return packs[0]

    def _pack_path(self) -> Path:
        return AREAS_ROOT / self.pack_relpath

    def _switch_pack(self, relpath: str) -> None:
        relpath = (relpath or "").replace("\\", "/").strip()
        if not relpath:
            return

        self.pack_relpath = relpath
        self.areas = self.load_areas()
        self.visible_areas = set(self.areas.keys())

        self.draw_areas()
        self.create_selection_window()
        print(f"📦 Pack actief: {self.pack_relpath}")

    def _slug(self, s: str) -> str:
        s = s.strip().lower().replace(" ", "_")
        keep = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        s = "".join(ch for ch in s if ch in keep)
        return s or "new_pack"

    def _create_new_pack_folder(self) -> None:
        name = simpledialog.askstring("Nieuw pack", "Naam (bijv. bank area):", parent=self)
        if not name:
            return

        folder = self._slug(name)
        path = AREAS_ROOT / folder / f"{folder}.json"
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            messagebox.showerror("Bestaat al", f"'{folder}/{folder}.json' bestaat al.")
            return

        path.write_text("{}", encoding="utf-8")

        rel = str(path.relative_to(AREAS_ROOT)).replace("\\", "/")
        self._switch_pack(rel)
        # dropdown refresh (als window open is)
        if hasattr(self, "pack_optionmenu"):
            self._refresh_pack_dropdown()

    def _ensure_pack_vars(self) -> None:
        if not hasattr(self, "pack_var"):
            self.pack_var = tk.StringVar(value=self.pack_relpath)
            self.pack_var.trace_add("write", lambda *_: self._switch_pack(self.pack_var.get()))

    def _refresh_pack_dropdown(self) -> None:
        packs = self._list_packs()
        menu = self.pack_optionmenu["menu"]
        menu.delete(0, "end")

        for p in packs:
            menu.add_command(label=p, command=lambda v=p: self.pack_var.set(v))

        if packs and self.pack_var.get() not in packs:
            self.pack_var.set(packs[0])

        if packs:
            self.pack_var.set(self.pack_relpath)

    # ----------------------------
    # IO
    # ----------------------------
    def load_areas(self) -> dict:
        path = self._pack_path()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
            return {}

        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            print(f"⚠️ {self.pack_relpath} kapot: {e}")
            return {}

        # support: categories -> flatten
        if isinstance(raw, dict) and raw and all(isinstance(v, dict) for v in raw.values()):
            flat = {}
            for _cat, sub in raw.items():
                for n, coords in sub.items():
                    flat[n] = coords
            return flat

        return raw if isinstance(raw, dict) else {}

    def save_areas(self) -> None:
        path = self._pack_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.areas, indent=2), encoding="utf-8")
        print(f"✅ opgeslagen: {self.pack_relpath}")

    # ----------------------------
    # Bot offsets
    # ----------------------------
    def create_bot_selector(self) -> None:
        frame = tk.Frame(self, bg="black")
        frame.place(x=20, y=20)

        tk.Label(frame, text="Bot ID:", bg="black", fg="white").pack(side="left")

        bot_var = tk.IntVar(value=self.bot_id)
        for i in range(1, 5):
            tk.Radiobutton(
                frame,
                text=str(i),
                variable=bot_var,
                value=i,
                command=lambda v=i: self.switch_bot(v),
                bg="black",
                fg="white",
                selectcolor="gray",
            ).pack(side="left")

    def switch_bot(self, new_id: int) -> None:
        self.bot_id = int(new_id)
        self.x_offset, self.y_offset = get_offset(self.bot_id)
        print(f"🔄 Bot {self.bot_id} offset=({self.x_offset},{self.y_offset})")
        self.draw_areas()
        self.create_selection_window()

    def offset_area(self, coords):
        x1, y1, x2, y2 = coords
        return [x1 + self.x_offset, y1 + self.y_offset, x2 + self.x_offset, y2 + self.y_offset]

    # ----------------------------
    # Drawing
    # ----------------------------
    def draw_areas(self) -> None:
        self.canvas.delete("all")
        self.rect_ids.clear()
        self.label_ids.clear()
        self.handle_ids.clear()

        for name, coords in self.areas.items():
            if name not in self.visible_areas or not (isinstance(coords, list) and len(coords) == 4):
                continue

            ox1, oy1, ox2, oy2 = self.offset_area(coords)
            color = self.get_bright_color()

            rect_id = self.canvas.create_rectangle(
                ox1, oy1, ox2, oy2, outline=color, width=3, tags=("area", name)
            )
            self.rect_ids[name] = rect_id

            label_id = self.canvas.create_text(
                ox1 + 5,
                oy1 - 14,
                text=f"{name} [Bot {self.bot_id}]",
                anchor="nw",
                fill=color,
                font=("Arial", 12, "bold"),
                tags=("label", name),
            )
            self.label_ids[name] = label_id

            self.draw_handles(name, ox1, oy1, ox2, oy2)

    def draw_handles(self, name, ox1, oy1, ox2, oy2) -> None:
        positions = self.handle_positions(ox1, oy1, ox2, oy2)
        self.handle_ids[name] = {}
        for pos, (cx, cy) in positions.items():
            hid = self.canvas.create_rectangle(
                cx - HANDLE_SIZE / 2,
                cy - HANDLE_SIZE / 2,
                cx + HANDLE_SIZE / 2,
                cy + HANDLE_SIZE / 2,
                fill=HANDLE_FILL,
                outline=HANDLE_OUTLINE,
                tags=("handle", name, f"handle-{pos}"),
            )
            self.handle_ids[name][pos] = hid

    def handle_positions(self, x1, y1, x2, y2):
        return {
            "nw": (x1 - HANDLE_OFFSET, y1 - HANDLE_OFFSET),
            "n": ((x1 + x2) / 2, y1 - HANDLE_OFFSET),
            "ne": (x2 + HANDLE_OFFSET, y1 - HANDLE_OFFSET),
            "e": (x2 + HANDLE_OFFSET, (y1 + y2) / 2),
            "se": (x2 + HANDLE_OFFSET, y2 + HANDLE_OFFSET),
            "s": ((x1 + x2) / 2, y2 + HANDLE_OFFSET),
            "sw": (x1 - HANDLE_OFFSET, y2 + HANDLE_OFFSET),
            "w": (x1 - HANDLE_OFFSET, (y1 + y2) / 2),
        }

    def get_bright_color(self) -> str:
        return f"#{random.randint(120, 255):02x}{random.randint(120, 255):02x}{random.randint(120, 255):02x}"

    # ----------------------------
    # Hit helpers
    # ----------------------------
    def find_handle_hit(self, x, y):
        pad = max(2, HANDLE_SIZE // 2 + 2)
        items = self.canvas.find_overlapping(x - pad, y - pad, x + pad, y + pad)
        for it in items:
            tags = set(self.canvas.gettags(it))
            if "handle" in tags:
                pos = None
                name = None
                for t in tags:
                    if t.startswith("handle-"):
                        pos = t.split("-", 1)[1]
                    elif t not in {"handle", "current"} and not t.startswith("handle-"):
                        name = t
                if name and pos:
                    return name, pos
        return None, None

    def find_area_hit(self, x, y):
        for name, coords in self.areas.items():
            if name not in self.visible_areas:
                continue
            ox1, oy1, ox2, oy2 = self.offset_area(coords)
            if ox1 <= x <= ox2 and oy1 <= y <= oy2:
                return name, (x - ox1), (y - oy1)
        return None, 0, 0

    # ----------------------------
    # Mouse logic
    # ----------------------------
    def on_mouse_down_left(self, event):
        name, pos = self.find_handle_hit(event.x, event.y)
        if name and pos:
            self.selected_area = name
            self.active_handle = pos
            self.drag_mode = "resize"
            return

        name, dx, dy = self.find_area_hit(event.x, event.y)
        if name:
            self.selected_area = name
            self.offset_x = dx
            self.offset_y = dy
            self.drag_mode = "move"
        else:
            self.selected_area = None
            self.drag_mode = None

    def on_mouse_drag_left(self, event):
        if self.drag_mode == "resize" and self.selected_area and self.active_handle:
            self._apply_resize(event.x, event.y)
        elif self.drag_mode == "move" and self.selected_area:
            self._apply_move(event.x, event.y)

    def on_mouse_up_left(self, event):
        if self.selected_area:
            self.save_areas()
        self.active_handle = None
        self.selected_area = None
        self.drag_mode = None

    # ----------------------------
    # Core move/resize (writes BASE coords)
    # ----------------------------
    def _apply_move(self, x, y):
        x1, y1, x2, y2 = self.areas[self.selected_area]
        new_x1 = x - self.offset_x - self.x_offset
        new_y1 = y - self.offset_y - self.y_offset
        w, h = x2 - x1, y2 - y1
        self.areas[self.selected_area] = [new_x1, new_y1, new_x1 + w, new_y1 + h]
        self.draw_areas()

    def _apply_resize(self, x, y):
        x1, y1, x2, y2 = self.areas[self.selected_area]
        ex = x - self.x_offset
        ey = y - self.y_offset
        min_size = 20

        if "w" in self.active_handle:
            x1 = min(ex, x2 - min_size)
        if "e" in self.active_handle:
            x2 = max(ex, x1 + min_size)
        if "n" in self.active_handle:
            y1 = min(ey, y2 - min_size)
        if "s" in self.active_handle:
            y2 = max(ey, y1 + min_size)

        self.areas[self.selected_area] = [x1, y1, x2, y2]
        self.draw_areas()

    # ----------------------------
    # Rename
    # ----------------------------
    def on_double_click_canvas(self, event):
        target = None
        for name, lbl_id in self.label_ids.items():
            bx = self.canvas.bbox(lbl_id)
            if bx and bx[0] <= event.x <= bx[2] and bx[1] <= event.y <= bx[3]:
                target = name
                break
        if not target:
            name, _, _ = self.find_area_hit(event.x, event.y)
            target = name

        if target:
            self.prompt_rename(target)

    def prompt_rename(self, old_name):
        new_name = simpledialog.askstring("Naam wijzigen", f"Nieuwe naam voor '{old_name}':", parent=self)
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name:
            return
        if new_name in self.areas and new_name != old_name:
            messagebox.showerror("Bestaat al", f"'{new_name}' bestaat al.")
            return

        self.areas[new_name] = self.areas.pop(old_name)
        if old_name in self.visible_areas:
            self.visible_areas.remove(old_name)
            self.visible_areas.add(new_name)

        self.save_areas()
        self.draw_areas()
        self.create_selection_window()

    # ----------------------------
    # Selection window
    # ----------------------------
    def create_selection_window(self):
        if hasattr(self, "selection_window"):
            self.selection_window.destroy()

        self.selection_window = tk.Toplevel(self)
        self.selection_window.title(f"Areas packs (Bot {self.bot_id})")
        self.selection_window.geometry(f"+{self.winfo_screenwidth() - 460}+100")
        self.selection_window.attributes("-topmost", True)
        self.selection_window.resizable(False, False)

        # Pack selector row
        self._ensure_pack_vars()

        top = tk.Frame(self.selection_window)
        top.pack(fill="x", padx=10, pady=(10, 6))

        tk.Label(top, text="Pack:").pack(side="left")

        self.pack_optionmenu = tk.OptionMenu(top, self.pack_var, "")
        self.pack_optionmenu.pack(side="left", fill="x", expand=True, padx=6)

        tk.Button(top, text="+ New pack", command=self._create_new_pack_folder).pack(side="right")

        self._refresh_pack_dropdown()

        # Search
        search_var = tk.StringVar()

        def filter_areas():
            for widget in self.areas_frame.winfo_children():
                widget.destroy()
            text = search_var.get().lower()
            for name, coords in self.areas.items():
                if text in name.lower():
                    build_row(name, coords)

        search_var.trace("w", lambda *args: filter_areas())

        search_entry = tk.Entry(self.selection_window, textvariable=search_var, font=("Arial", 11))
        search_entry.pack(fill="x", padx=10, pady=(0, 5))

        btn_frame = tk.Frame(self.selection_window)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="✅ Alles", command=self.select_all).pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(btn_frame, text="❌ Niets", command=self.deselect_all).pack(side="right", expand=True, fill="x", padx=5)

        canvas_frame = tk.Frame(self.selection_window)
        canvas_frame.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        self.selection_canvas = tk.Canvas(canvas_frame, height=340)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.selection_canvas.yview)
        self.areas_frame = tk.Frame(self.selection_canvas)

        self.areas_frame.bind(
            "<Configure>",
            lambda e: self.selection_canvas.configure(scrollregion=self.selection_canvas.bbox("all")),
        )

        self.selection_canvas.create_window((0, 0), window=self.areas_frame, anchor="nw")
        self.selection_canvas.configure(yscrollcommand=scrollbar.set)
        self.selection_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.check_vars = {}

        def build_row(name, coords):
            row = tk.Frame(self.areas_frame)
            row.pack(fill="x", padx=4, pady=1)

            var = self.check_vars.get(name)
            if not var:
                var = tk.BooleanVar(value=(name in self.visible_areas))
                self.check_vars[name] = var

            cb = tk.Checkbutton(row, variable=var, command=self.update_visible_areas)
            cb.pack(side="left")

            coords_offset = self.offset_area(coords)
            lbl = tk.Label(row, text=f"{name} {coords_offset}", anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Double-Button-1>", lambda e, n=name: self.prompt_rename(n))

            tk.Button(row, text="✎", width=2, command=lambda n=name: self.prompt_rename(n)).pack(side="right", padx=2)

        filter_areas()

        tk.Button(self.selection_window, text="+ Nieuw gebied", command=self.add_new_area).pack(
            fill="x", padx=10, pady=(0, 10)
        )

    def select_all(self):
        for var in self.check_vars.values():
            var.set(True)
        self.update_visible_areas()

    def deselect_all(self):
        for var in self.check_vars.values():
            var.set(False)
        self.update_visible_areas()

    def update_visible_areas(self):
        self.visible_areas = {name for name, var in self.check_vars.items() if var.get()}
        self.draw_areas()

    def add_new_area(self):
        base = "NieuwGebied"
        i = 1
        while f"{base}_{i}" in self.areas:
            i += 1
        name = f"{base}_{i}"
        self.areas[name] = [100, 100, 200, 200]
        self.visible_areas.add(name)
        self.save_areas()
        self.draw_areas()
        self.create_selection_window()
        print(f"🆕 Gebied '{name}' toegevoegd.")


if __name__ == "__main__":
    AreaOverlay().mainloop()
