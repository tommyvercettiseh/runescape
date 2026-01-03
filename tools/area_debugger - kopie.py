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
# Single areas file
# ----------------------------
AREAS_FILE = ROOT / "config" / "areas.json"
AREAS_FILE.parent.mkdir(parents=True, exist_ok=True)
if not AREAS_FILE.exists():
    AREAS_FILE.write_text("{}", encoding="utf-8")

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

        # State
        self.selected_area = None
        self.active_handle = None
        self.drag_mode = None
        self.offset_x = 0
        self.offset_y = 0

        self.rect_ids = {}
        self.label_ids = {}
        self.handle_ids = {}

        # Bot offsets
        self.bot_id = 1
        self.x_offset, self.y_offset = get_offset(self.bot_id)

        # Data
        self.data = self.load_areas()
        self.group_filter = "all"
        self.visible_areas = set(self.data.keys())

        # History (coords only)
        self.undo_stack: dict[str, list[list[int]]] = {}  # per area: [coords_before, ...]
        self.redo_stack: dict[str, list[list[int]]] = {}  # per area: [coords_after_undo, ...]
        self._edit_started = False
        self._edit_area_name: str | None = None

        # Deleted areas (undo delete)
        self.deleted_stack: list[tuple[str, dict]] = []

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
    # IO
    # ----------------------------
    def load_areas(self) -> dict:
        try:
            raw = json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            print(f"⚠️ areas.json kapot: {e}")
            return {}

        # Backwards compat: {"name":[x1,y1,x2,y2]} -> {"name":{"coords":[..],"group":"default"}}
        fixed = {}
        for name, v in (raw or {}).items():
            if isinstance(v, list) and len(v) == 4:
                fixed[name] = {"coords": v, "group": "default"}
            elif isinstance(v, dict) and isinstance(v.get("coords"), list) and len(v["coords"]) == 4:
                fixed[name] = {"coords": v["coords"], "group": (v.get("group") or "default")}
        return fixed

    def save_areas(self) -> None:
        AREAS_FILE.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        print("✅ opgeslagen: areas.json")

    # ----------------------------
    # History helpers (coords only)
    # ----------------------------
    def _history_init(self, name: str) -> None:
        self.undo_stack.setdefault(name, [])
        self.redo_stack.setdefault(name, [])

    def _record_before_edit(self, name: str) -> None:
        # record 1x per drag/edit session
        if self._edit_started and self._edit_area_name == name:
            return

        self._history_init(name)
        cur = list(self.data[name]["coords"])
        self.undo_stack[name].append(cur)
        self.redo_stack[name].clear()

        self._edit_started = True
        self._edit_area_name = name

    def undo_area(self, name: str) -> None:
        self._history_init(name)
        if not self.undo_stack[name]:
            return

        cur = list(self.data[name]["coords"])
        prev = self.undo_stack[name].pop()

        self.redo_stack[name].append(cur)
        self.data[name]["coords"] = prev

        self.save_areas()
        self.draw_areas()
        self.create_selection_window()

    def redo_area(self, name: str) -> None:
        self._history_init(name)
        if not self.redo_stack[name]:
            return

        cur = list(self.data[name]["coords"])
        nxt = self.redo_stack[name].pop()

        self.undo_stack[name].append(cur)
        self.data[name]["coords"] = nxt

        self.save_areas()
        self.draw_areas()
        self.create_selection_window()

    # ----------------------------
    # Delete helpers
    # ----------------------------
    def delete_area(self, name: str) -> None:
        if name not in self.data:
            return

        if not messagebox.askyesno("Verwijderen", f"'{name}' verwijderen?", parent=self.selection_window):
            return

        payload = self.data.pop(name)
        self.deleted_stack.append((name, payload))

        self.visible_areas.discard(name)
        self.undo_stack.pop(name, None)
        self.redo_stack.pop(name, None)

        self.save_areas()
        self.draw_areas()
        self.create_selection_window()

    def undo_delete(self) -> None:
        if not self.deleted_stack:
            return
        name, payload = self.deleted_stack.pop()
        if name in self.data:
            # als naam alweer bestaat, pak suffix
            base = name
            i = 2
            while f"{base}_{i}" in self.data:
                i += 1
            name = f"{base}_{i}"

        self.data[name] = payload
        self.visible_areas.add(name)
        self._history_init(name)

        self.save_areas()
        self.draw_areas()
        self.create_selection_window()

    # ----------------------------
    # Helpers
    # ----------------------------
    def get_groups(self) -> list[str]:
        groups = sorted({(v.get("group") or "default") for v in self.data.values()})
        return ["all"] + groups

    def offset_area(self, coords):
        x1, y1, x2, y2 = coords
        return [x1 + self.x_offset, y1 + self.y_offset, x2 + self.x_offset, y2 + self.y_offset]

    def get_bright_color(self) -> str:
        return f"#{random.randint(120, 255):02x}{random.randint(120, 255):02x}{random.randint(120, 255):02x}"

    def filtered_names(self) -> list[str]:
        names = []
        for name, obj in self.data.items():
            g = (obj.get("group") or "default")
            if self.group_filter != "all" and g != self.group_filter:
                continue
            names.append(name)
        return names

    # ----------------------------
    # Bot selector
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

    # ----------------------------
    # Drawing
    # ----------------------------
    def draw_areas(self) -> None:
        self.canvas.delete("all")
        self.rect_ids.clear()
        self.label_ids.clear()
        self.handle_ids.clear()

        for name in self.filtered_names():
            if name not in self.visible_areas:
                continue

            coords = self.data[name]["coords"]
            ox1, oy1, ox2, oy2 = self.offset_area(coords)
            color = self.get_bright_color()

            rect_id = self.canvas.create_rectangle(
                ox1, oy1, ox2, oy2, outline=color, width=3, tags=("area", name)
            )
            self.rect_ids[name] = rect_id

            g = self.data[name].get("group") or "default"
            label_id = self.canvas.create_text(
                ox1 + 5,
                oy1 - 14,
                text=f"{name} ({g}) [Bot {self.bot_id}]",
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
        for name in self.filtered_names():
            if name not in self.visible_areas:
                continue
            coords = self.data[name]["coords"]
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
            self._record_before_edit(name)
            return

        name, dx, dy = self.find_area_hit(event.x, event.y)
        if name:
            self.selected_area = name
            self.offset_x = dx
            self.offset_y = dy
            self.drag_mode = "move"
            self._record_before_edit(name)
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

        self._edit_started = False
        self._edit_area_name = None

    # ----------------------------
    # Core move/resize (writes BASE coords)
    # ----------------------------
    def _apply_move(self, x, y):
        x1, y1, x2, y2 = self.data[self.selected_area]["coords"]
        new_x1 = x - self.offset_x - self.x_offset
        new_y1 = y - self.offset_y - self.y_offset
        w, h = x2 - x1, y2 - y1
        self.data[self.selected_area]["coords"] = [new_x1, new_y1, new_x1 + w, new_y1 + h]
        self.draw_areas()

    def _apply_resize(self, x, y):
        x1, y1, x2, y2 = self.data[self.selected_area]["coords"]
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

        self.data[self.selected_area]["coords"] = [x1, y1, x2, y2]
        self.draw_areas()

    # ----------------------------
    # Rename + group edit
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
        if new_name in self.data and new_name != old_name:
            messagebox.showerror("Bestaat al", f"'{new_name}' bestaat al.")
            return

        self.data[new_name] = self.data.pop(old_name)

        # move history too
        if old_name in self.undo_stack:
            self.undo_stack[new_name] = self.undo_stack.pop(old_name)
        if old_name in self.redo_stack:
            self.redo_stack[new_name] = self.redo_stack.pop(old_name)

        if old_name in self.visible_areas:
            self.visible_areas.remove(old_name)
            self.visible_areas.add(new_name)

        self.save_areas()
        self.draw_areas()
        self.create_selection_window()

    def prompt_group(self, name: str):
        cur = (self.data[name].get("group") or "default")
        g = simpledialog.askstring("Group", f"Group voor '{name}':", initialvalue=cur, parent=self)
        if not g:
            return
        g = g.strip() or "default"
        self.data[name]["group"] = g
        self.save_areas()
        self.create_selection_window()
        self.draw_areas()

    # ----------------------------
    # Selection window
    # ----------------------------
    def create_selection_window(self):
        if hasattr(self, "selection_window"):
            self.selection_window.destroy()

        self.selection_window = tk.Toplevel(self)
        self.selection_window.title(f"Areas (Bot {self.bot_id})")
        self.selection_window.geometry(f"+{self.winfo_screenwidth() - 520}+100")
        self.selection_window.attributes("-topmost", True)
        self.selection_window.resizable(False, False)

        # Group filter row
        top = tk.Frame(self.selection_window)
        top.pack(fill="x", padx=10, pady=(10, 6))

        tk.Label(top, text="Group:").pack(side="left")

        self.group_var = tk.StringVar(value=self.group_filter)

        def on_group_change(*_):
            self.group_filter = self.group_var.get()
            self.visible_areas = set(self.filtered_names())
            self.draw_areas()
            rebuild_list()

        self.group_var.trace_add("write", on_group_change)

        groups = self.get_groups()
        self.group_menu = tk.OptionMenu(top, self.group_var, *groups)
        self.group_menu.pack(side="left", fill="x", expand=True, padx=6)

        tk.Button(top, text="+ New area", command=self.add_new_area).pack(side="right")

        # Undo delete row
        ud = tk.Frame(self.selection_window)
        ud.pack(fill="x", padx=10, pady=(0, 6))
        tk.Button(
            ud,
            text="↩ Undo delete",
            command=self.undo_delete,
            state=("normal" if self.deleted_stack else "disabled"),
        ).pack(side="left", fill="x", expand=True)

        # Search
        search_var = tk.StringVar()

        def rebuild_list():
            for w in self.areas_frame.winfo_children():
                w.destroy()

            text = search_var.get().lower().strip()
            for name in self.filtered_names():
                if text and text not in name.lower():
                    continue
                build_row(name)

        search_var.trace("w", lambda *_: rebuild_list())

        search_entry = tk.Entry(self.selection_window, textvariable=search_var, font=("Arial", 11))
        search_entry.pack(fill="x", padx=10, pady=(0, 5))

        btn_frame = tk.Frame(self.selection_window)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="✅ Alles", command=self.select_all).pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(btn_frame, text="❌ Niets", command=self.deselect_all).pack(side="right", expand=True, fill="x", padx=5)

        canvas_frame = tk.Frame(self.selection_window)
        canvas_frame.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        self.selection_canvas = tk.Canvas(canvas_frame, height=360)
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

        def build_row(name):
            row = tk.Frame(self.areas_frame)
            row.pack(fill="x", padx=4, pady=1)

            var = self.check_vars.get(name)
            if not var:
                var = tk.BooleanVar(value=(name in self.visible_areas))
                self.check_vars[name] = var

            tk.Checkbutton(row, variable=var, command=self.update_visible_areas).pack(side="left")

            coords = self.data[name]["coords"]
            coords_offset = self.offset_area(coords)
            g = (self.data[name].get("group") or "default")
            lbl = tk.Label(row, text=f"{name} ({g}) {coords_offset}", anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Double-Button-1>", lambda e, n=name: self.prompt_rename(n))

            self._history_init(name)
            can_undo = bool(self.undo_stack.get(name))
            can_redo = bool(self.redo_stack.get(name))

            tk.Button(row, text="⟲", width=2, command=lambda n=name: self.undo_area(n),
                      state=("normal" if can_undo else "disabled")).pack(side="right", padx=2)
            tk.Button(row, text="⟳", width=2, command=lambda n=name: self.redo_area(n),
                      state=("normal" if can_redo else "disabled")).pack(side="right", padx=2)
            tk.Button(row, text="🗑", width=2, command=lambda n=name: self.delete_area(n)).pack(side="right", padx=2)

            tk.Button(row, text="G", width=2, command=lambda n=name: self.prompt_group(n)).pack(side="right", padx=2)
            tk.Button(row, text="✎", width=2, command=lambda n=name: self.prompt_rename(n)).pack(side="right", padx=2)

        rebuild_list()

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
        while f"{base}_{i}" in self.data:
            i += 1
        name = f"{base}_{i}"

        g = self.group_filter if self.group_filter != "all" else "default"
        self.data[name] = {"coords": [100, 100, 200, 200], "group": g}
        self.visible_areas.add(name)

        self._history_init(name)

        self.save_areas()
        self.draw_areas()
        self.create_selection_window()
        print(f"🆕 Gebied '{name}' toegevoegd in group '{g}'.")


if __name__ == "__main__":
    AreaOverlay().mainloop()
