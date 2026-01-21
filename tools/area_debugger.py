from __future__ import annotations

import json
import random
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

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

GRID_LINE_COLOR = "#00ff66"
GRID_ROI_COLOR = "#ffcc00"
GRID_TEXT_COLOR = "#ffffff"


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

        # Grid overlay ids
        self.grid_ids = []
        self.grid_text_ids = []

        # Bot offsets
        self.bot_id = 1
        self.x_offset, self.y_offset = get_offset(self.bot_id)

        # Data
        self.data = self.load_areas()

        # Visible areas only
        self.visible_areas = set(self.data.keys())

        # History (coords only)
        self.undo_stack = {}
        self.redo_stack = {}
        self._edit_started = False
        self._edit_area_name = None

        # Deleted areas (undo delete)
        self.deleted_stack = []

        # Grid tool state
        self.grid_parent_name = ""
        self.grid_cols = 4
        self.grid_rows = 7
        self.grid_roi_pct = 40
        self.grid_show = False

        # Slot prefix override
        self.grid_slot_prefix_override = ""

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
    def load_areas(self):
        try:
            raw = json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            print(f"⚠️ areas.json kapot: {e}")
            return {}

        fixed = {}
        for name, v in (raw or {}).items():
            if isinstance(v, list) and len(v) == 4:
                fixed[name] = {"coords": v, "group": "default"}
            elif isinstance(v, dict) and isinstance(v.get("coords"), list) and len(v["coords"]) == 4:
                fixed[name] = {"coords": v["coords"], "group": (v.get("group") or "default")}
        return fixed

    def save_areas(self):
        AREAS_FILE.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        print("✅ opgeslagen: areas.json")

    # ----------------------------
    # History helpers
    # ----------------------------
    def _history_init(self, name):
        self.undo_stack.setdefault(name, [])
        self.redo_stack.setdefault(name, [])

    def _record_before_edit(self, name):
        if self._edit_started and self._edit_area_name == name:
            return
        self._history_init(name)
        cur = list(self.data[name]["coords"])
        self.undo_stack[name].append(cur)
        self.redo_stack[name].clear()
        self._edit_started = True
        self._edit_area_name = name

    def undo_area(self, name):
        self._history_init(name)
        if not self.undo_stack[name]:
            return
        cur = list(self.data[name]["coords"])
        prev = self.undo_stack[name].pop()
        self.redo_stack[name].append(cur)
        self.data[name]["coords"] = prev
        self.save_areas()
        self.draw_areas()
        self.rebuild_tree()

    def redo_area(self, name):
        self._history_init(name)
        if not self.redo_stack[name]:
            return
        cur = list(self.data[name]["coords"])
        nxt = self.redo_stack[name].pop()
        self.undo_stack[name].append(cur)
        self.data[name]["coords"] = nxt
        self.save_areas()
        self.draw_areas()
        self.rebuild_tree()

    # ----------------------------
    # Delete helpers
    # ----------------------------
    def delete_area(self, name):
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
        self.rebuild_tree()
        self._refresh_undo_delete_btn()

    def undo_delete(self):
        if not self.deleted_stack:
            return
        name, payload = self.deleted_stack.pop()

        if name in self.data:
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
        self.rebuild_tree()
        self._refresh_undo_delete_btn()

    # ----------------------------
    # Helpers
    # ----------------------------
    def offset_area(self, coords):
        x1, y1, x2, y2 = coords
        return [x1 + self.x_offset, y1 + self.y_offset, x2 + self.x_offset, y2 + self.y_offset]

    def get_bright_color(self):
        return f"#{random.randint(120, 255):02x}{random.randint(120, 255):02x}{random.randint(120, 255):02x}"

    def _get_group(self, name: str) -> str:
        return (self.data.get(name, {}).get("group") or "default")

    def _is_visible(self, name: str) -> bool:
        return name in self.visible_areas

    def _set_visible(self, name: str, visible: bool):
        if visible:
            self.visible_areas.add(name)
        else:
            self.visible_areas.discard(name)

    # ----------------------------
    # Grid naming helpers
    # ----------------------------
    def _grid_slot_prefix_for_parent(self, parent):
        if self.grid_slot_prefix_override:
            return self.grid_slot_prefix_override.strip()
        base = str(parent).strip()
        if base.lower().endswith("_area"):
            base = base[:-5]
        return f"{base}_Slot_"

    def _set_grid_parent(self, name):
        name = (name or "").strip()
        if not name or name not in self.data:
            return
        self.grid_parent_name = name
        if hasattr(self, "grid_parent_var"):
            try:
                self.grid_parent_var.set(name)
            except Exception:
                pass
        self.draw_areas()

    # ----------------------------
    # Bot selector
    # ----------------------------
    def create_bot_selector(self):
        frame = tk.Frame(self, bg="black")
        frame.place(x=20, y=20)

        tk.Label(frame, text="Bot ID:", bg="black", fg="white").pack(side="left")

        bot_var = tk.IntVar(value=self.bot_id)
        for i in (1, 2, 3, 4):
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

    def switch_bot(self, new_id):
        self.bot_id = int(new_id)
        self.x_offset, self.y_offset = get_offset(self.bot_id)
        print(f"🔄 Bot {self.bot_id} offset=({self.x_offset},{self.y_offset})")
        self.draw_areas()
        self.rebuild_tree()

    # ----------------------------
    # Drawing
    # ----------------------------
    def draw_areas(self):
        self.canvas.delete("all")
        self.rect_ids.clear()
        self.label_ids.clear()
        self.handle_ids.clear()

        for name, obj in self.data.items():
            if name not in self.visible_areas:
                continue

            coords = obj["coords"]
            ox1, oy1, ox2, oy2 = self.offset_area(coords)
            color = self.get_bright_color()

            rect_id = self.canvas.create_rectangle(
                ox1, oy1, ox2, oy2, outline=color, width=3, tags=("area", name)
            )
            self.rect_ids[name] = rect_id

            g = (obj.get("group") or "default")
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

        self._draw_grid_overlay()

    def draw_handles(self, name, ox1, oy1, ox2, oy2):
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
    # Grid overlay
    # ----------------------------
    def _clear_grid_overlay(self):
        for it in self.grid_ids:
            try:
                self.canvas.delete(it)
            except Exception:
                pass
        for it in self.grid_text_ids:
            try:
                self.canvas.delete(it)
            except Exception:
                pass
        self.grid_ids = []
        self.grid_text_ids = []

    def _calc_grid_rois_base(self, base_xyxy, cols, rows, roi_pct):
        x1, y1, x2, y2 = base_xyxy
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)

        cw = w / max(1, cols)
        ch = h / max(1, rows)

        roi_scale = max(5, min(100, int(roi_pct))) / 100.0

        out = []
        idx = 0
        for r in range(rows):
            for c in range(cols):
                cx1 = x1 + c * cw
                cy1 = y1 + r * ch
                cx2 = cx1 + cw
                cy2 = cy1 + ch

                ccx = (cx1 + cx2) / 2
                ccy = (cy1 + cy2) / 2
                rw = cw * roi_scale
                rh = ch * roi_scale

                rx1 = int(ccx - rw / 2)
                ry1 = int(ccy - rh / 2)
                rx2 = int(ccx + rw / 2)
                ry2 = int(ccy + rh / 2)

                out.append((idx, int(cx1), int(cy1), int(cx2), int(cy2), rx1, ry1, rx2, ry2))
                idx += 1

        return out

    def _draw_grid_overlay(self):
        self._clear_grid_overlay()

        if not self.grid_show:
            return
        if not self.grid_parent_name:
            return
        if self.grid_parent_name not in self.data:
            return
        if self.grid_parent_name not in self.visible_areas:
            return

        base = self.data[self.grid_parent_name]["coords"]
        cols = int(self.grid_cols)
        rows = int(self.grid_rows)
        roi_pct = int(self.grid_roi_pct)

        rois = self._calc_grid_rois_base(base, cols, rows, roi_pct)

        for idx, cx1, cy1, cx2, cy2, rx1, ry1, rx2, ry2 in rois:
            ox1, oy1, ox2, oy2 = self.offset_area([cx1, cy1, cx2, cy2])
            orx1, ory1, orx2, ory2 = self.offset_area([rx1, ry1, rx2, ry2])

            gid = self.canvas.create_rectangle(ox1, oy1, ox2, oy2, outline=GRID_LINE_COLOR, width=1)
            self.grid_ids.append(gid)

            rid = self.canvas.create_rectangle(orx1, ory1, orx2, ory2, outline=GRID_ROI_COLOR, width=2)
            self.grid_ids.append(rid)

            tx = (orx1 + orx2) // 2
            ty = (ory1 + ory2) // 2
            tid = self.canvas.create_text(
                tx, ty, text=str(idx + 1), fill=GRID_TEXT_COLOR, font=("Arial", 10, "bold")
            )
            self.grid_text_ids.append(tid)

    def _grid_refresh_from_ui(self):
        if hasattr(self, "grid_parent_var"):
            self.grid_parent_name = (self.grid_parent_var.get() or "").strip()
        if hasattr(self, "grid_cols_var"):
            self.grid_cols = int(self.grid_cols_var.get())
        if hasattr(self, "grid_rows_var"):
            self.grid_rows = int(self.grid_rows_var.get())
        if hasattr(self, "grid_roi_var"):
            self.grid_roi_pct = int(self.grid_roi_var.get())
        if hasattr(self, "grid_show_var"):
            self.grid_show = bool(self.grid_show_var.get())
        self.draw_areas()

    def save_grid_as_areas(self):
        parent = (self.grid_parent_var.get() or "").strip()
        if not parent or parent not in self.data:
            return messagebox.showerror("Grid", "Kies eerst een area (bv Inventory_Area)", parent=self.selection_window)

        if "_Slot_" in parent or parent.lower().endswith("_slots") or parent.lower().endswith("_grid"):
            return messagebox.showerror("Grid", f"Deze parent lijkt al een slot of grid:\n{parent}", parent=self.selection_window)

        cols = int(self.grid_cols_var.get())
        rows = int(self.grid_rows_var.get())
        roi_pct = int(self.grid_roi_var.get())

        base = self.data[parent]["coords"]
        rois = self._calc_grid_rois_base(base, cols, rows, roi_pct)

        prefix = self._grid_slot_prefix_for_parent(parent)
        grid_group = f"{prefix[:-6]}_Slots" if prefix.endswith("_Slot_") else f"{parent}_Slots"

        existing = [k for k in self.data.keys() if k.startswith(prefix)]
        if existing:
            if not messagebox.askyesno(
                "Grid",
                f"Er bestaan al {len(existing)} slots met prefix:\n{prefix}\n\nOverschrijven?",
                parent=self.selection_window,
            ):
                return
            for k in existing:
                self.data.pop(k, None)
                self.visible_areas.discard(k)
                self.undo_stack.pop(k, None)
                self.redo_stack.pop(k, None)

        for idx, _, _, _, _, rx1, ry1, rx2, ry2 in rois:
            name = f"{prefix}{idx + 1}"
            self.data[name] = {"coords": [rx1, ry1, rx2, ry2], "group": grid_group}
            self.visible_areas.add(name)
            self._history_init(name)

        self.save_areas()
        self.draw_areas()
        self.rebuild_tree()
        messagebox.showinfo("✅ Slots saved", f"{rows*cols} slots gemaakt\nPrefix: {prefix}", parent=self.selection_window)

    def delete_saved_grid(self):
        parent = (self.grid_parent_var.get() or "").strip()
        if not parent:
            return
        prefix = self._grid_slot_prefix_for_parent(parent)
        keys = [k for k in self.data.keys() if k.startswith(prefix)]
        if not keys:
            return messagebox.showinfo("Grid", "Geen slots gevonden voor deze area.", parent=self.selection_window)

        if not messagebox.askyesno("Grid", f"{len(keys)} slots verwijderen?\nPrefix: {prefix}", parent=self.selection_window):
            return

        for k in keys:
            self.data.pop(k, None)
            self.visible_areas.discard(k)
            self.undo_stack.pop(k, None)
            self.redo_stack.pop(k, None)

        self.save_areas()
        self.draw_areas()
        self.rebuild_tree()

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
                        pos = t.split("handle-", 1)[1]
                    elif t not in {"handle", "current"} and not t.startswith("handle-"):
                        name = t
                if name and pos:
                    return name, pos
        return None, None

    def find_area_hit(self, x, y):
        for name, obj in self.data.items():
            if name not in self.visible_areas:
                continue
            coords = obj["coords"]
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
            self._set_grid_parent(name)
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
            self.rebuild_tree()

        self.active_handle = None
        self.selected_area = None
        self.drag_mode = None
        self._edit_started = False
        self._edit_area_name = None

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
        if old_name not in self.data:
            return
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

        if old_name in self.undo_stack:
            self.undo_stack[new_name] = self.undo_stack.pop(old_name)
        if old_name in self.redo_stack:
            self.redo_stack[new_name] = self.redo_stack.pop(old_name)

        if old_name in self.visible_areas:
            self.visible_areas.remove(old_name)
            self.visible_areas.add(new_name)

        if self.grid_parent_name == old_name:
            self.grid_parent_name = new_name

        self.save_areas()
        self.draw_areas()
        self.rebuild_tree()

    def prompt_group(self, name):
        if name not in self.data:
            return
        cur = (self.data[name].get("group") or "default")
        g = simpledialog.askstring("Group", f"Group voor '{name}':", initialvalue=cur, parent=self.selection_window)
        if not g:
            return
        g = g.strip() or "default"
        self.data[name]["group"] = g
        self.save_areas()
        self.draw_areas()
        self.rebuild_tree()

    # ----------------------------
    # Tree model
    # ----------------------------
    def _slot_prefix_for_parent(self, parent_name: str) -> str:
        base = (parent_name or "").strip()
        if base.lower().endswith("_area"):
            base = base[:-5]
        return f"{base}_Slot_"

    def _build_group_map(self):
        groups = {}
        for name in self.data.keys():
            groups.setdefault(self._get_group(name), []).append(name)
        for g in groups:
            groups[g].sort()
        return groups

    def _find_children_slots(self, parent_area: str):
        prefix = self._slot_prefix_for_parent(parent_area)
        kids = [k for k in self.data.keys() if k.startswith(prefix)]
        def slot_num(n):
            tail = n.split(prefix, 1)[-1]
            return int(tail) if tail.isdigit() else 999999
        return sorted(kids, key=slot_num)

    # ----------------------------
    # Selection window (Tree UI)
    # ----------------------------
    def create_selection_window(self):
        self.selection_window = tk.Toplevel(self)
        self.selection_window.title(f"Areas (Bot {self.bot_id})")
        self.selection_window.geometry(f"+{self.winfo_screenwidth() - 660}+80")
        self.selection_window.attributes("-topmost", True)
        self.selection_window.resizable(True, True)

        # Top row
        top = tk.Frame(self.selection_window)
        top.pack(fill="x", padx=10, pady=(10, 6))

        tk.Label(top, text="Search").pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(top, textvariable=self.search_var, font=("Arial", 11)).pack(side="left", fill="x", expand=True, padx=8)

        tk.Button(top, text="+ New area", command=self.add_new_area).pack(side="right")

        # Undo delete row
        ud = tk.Frame(self.selection_window)
        ud.pack(fill="x", padx=10, pady=(0, 8))
        self.undo_delete_btn = tk.Button(
            ud,
            text="↩ Undo delete",
            command=self.undo_delete,
        )
        self.undo_delete_btn.pack(side="left", fill="x", expand=True)
        self._refresh_undo_delete_btn()

        # Grid Tool box
        gridbox = tk.LabelFrame(self.selection_window, text="Grid tool (parent → cells → centre ROI)")
        gridbox.pack(fill="x", padx=10, pady=(0, 8))

        names_for_grid = sorted(self.data.keys())
        if not self.grid_parent_name and names_for_grid:
            self.grid_parent_name = names_for_grid[0]

        self.grid_parent_var = tk.StringVar(value=self.grid_parent_name)
        self.grid_cols_var = tk.IntVar(value=int(self.grid_cols))
        self.grid_rows_var = tk.IntVar(value=int(self.grid_rows))
        self.grid_roi_var = tk.IntVar(value=int(self.grid_roi_pct))
        self.grid_show_var = tk.BooleanVar(value=bool(self.grid_show))

        row1 = tk.Frame(gridbox)
        row1.pack(fill="x", padx=8, pady=6)
        tk.Label(row1, text="Parent area").pack(side="left")
        self.parent_menu = tk.OptionMenu(row1, self.grid_parent_var, *names_for_grid)
        self.parent_menu.pack(side="left", fill="x", expand=True, padx=8)
        tk.Checkbutton(row1, text="Show grid", variable=self.grid_show_var, command=self._grid_refresh_from_ui).pack(side="right")

        row2 = tk.Frame(gridbox)
        row2.pack(fill="x", padx=8, pady=(0, 6))
        tk.Label(row2, text="Cols").pack(side="left")
        tk.Scale(row2, from_=1, to=12, orient="horizontal", variable=self.grid_cols_var, command=lambda *_: self._grid_refresh_from_ui(), length=160).pack(side="left", padx=6)
        tk.Label(row2, text="Rows").pack(side="left")
        tk.Scale(row2, from_=1, to=12, orient="horizontal", variable=self.grid_rows_var, command=lambda *_: self._grid_refresh_from_ui(), length=160).pack(side="left", padx=6)

        row3 = tk.Frame(gridbox)
        row3.pack(fill="x", padx=8, pady=(0, 6))
        tk.Label(row3, text="ROI size % (centre)").pack(side="left")
        tk.Scale(row3, from_=5, to=100, orient="horizontal", variable=self.grid_roi_var, command=lambda *_: self._grid_refresh_from_ui(), length=340).pack(side="left", padx=6)
        tk.Label(row3, text="(kleiner = strakker)").pack(side="left")

        self.grid_slot_prefix_var = tk.StringVar(value=self.grid_slot_prefix_override)
        rowN = tk.Frame(gridbox)
        rowN.pack(fill="x", padx=8, pady=(0, 6))
        tk.Label(rowN, text="Slot prefix (optional)").pack(side="left")
        tk.Entry(rowN, textvariable=self.grid_slot_prefix_var, width=24).pack(side="left", padx=6)
        tk.Label(rowN, text="(leeg = auto)").pack(side="left")

        def _apply_slot_prefix(*_):
            self.grid_slot_prefix_override = (self.grid_slot_prefix_var.get() or "").strip()
        self.grid_slot_prefix_var.trace_add("write", _apply_slot_prefix)

        row4 = tk.Frame(gridbox)
        row4.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(row4, text="💾 Save slots", command=self.save_grid_as_areas).pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(row4, text="🧹 Delete slots", command=self.delete_saved_grid).pack(side="left", fill="x", expand=True)

        self.grid_parent_var.trace_add("write", lambda *_: self._grid_refresh_from_ui())

        # Tree
        tree_frame = tk.Frame(self.selection_window)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(tree_frame, columns=("vis", "coords"), show="tree headings")
        self.tree.heading("#0", text="Name")
        self.tree.heading("vis", text="👁")
        self.tree.heading("coords", text="Coords (offset)")
        self.tree.column("vis", width=46, anchor="center", stretch=False)
        self.tree.column("coords", width=280, anchor="w", stretch=True)

        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        # Context menu
        self.ctx = tk.Menu(self.selection_window, tearoff=0)
        self.ctx.add_command(label="Rename", command=self._ctx_rename)
        self.ctx.add_command(label="Group", command=self._ctx_group)
        self.ctx.add_separator()
        self.ctx.add_command(label="Delete", command=self._ctx_delete)

        self._tree_node_kind = {}   # node_id -> "group"|"parent"|"area"|"slot"
        self._tree_node_name = {}   # node_id -> area_name or synthetic key
        self._ctx_target_node = None

        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Button-3>", self._on_tree_right_click)
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)

        self.search_var.trace_add("write", lambda *_: self.rebuild_tree())

        self.rebuild_tree()

    def _refresh_undo_delete_btn(self):
        if hasattr(self, "undo_delete_btn"):
            self.undo_delete_btn.configure(state=("normal" if self.deleted_stack else "disabled"))

    def rebuild_tree(self):
        if not hasattr(self, "tree"):
            return

        q = (self.search_var.get() or "").strip().lower()

        self.tree.delete(*self.tree.get_children())
        self._tree_node_kind.clear()
        self._tree_node_name.clear()

        groups = self._build_group_map()

        def matches(name: str) -> bool:
            if not q:
                return True
            return q in name.lower()

        def add_area_node(parent_id, area_name):
            coords_offset = self.offset_area(self.data[area_name]["coords"])
            vis = "✅" if self._is_visible(area_name) else ""
            nid = self.tree.insert(parent_id, "end", text=area_name, values=(vis, str(coords_offset)))
            self._tree_node_kind[nid] = "area"
            self._tree_node_name[nid] = area_name
            return nid

        # Build grouped, with parents and slots collapsible
        for gname in sorted(groups.keys()):
            area_names = groups[gname]

            # filter group if searching: keep group if any child matches
            if q and not any(matches(n) for n in area_names):
                continue

            gid = self.tree.insert("", "end", text=gname, values=("", ""))
            self._tree_node_kind[gid] = "group"
            self._tree_node_name[gid] = gname

            # Build parent nodes only for areas that have slots
            slot_parents = {}
            for n in area_names:
                kids = self._find_children_slots(n)
                if kids:
                    slot_parents[n] = kids

            # For each area in group
            for n in area_names:
                kids = slot_parents.get(n, [])
                is_parent = bool(kids)

                # Search behavior:
                # if parent matches, show parent and (optionally) show kids (still collapsed)
                # if a kid matches, show parent and only matching kids
                if not q:
                    show_parent = True
                    show_kids = True
                    kid_filter = None
                else:
                    parent_match = matches(n)
                    kid_matches = [k for k in kids if matches(k)]
                    show_parent = parent_match or bool(kid_matches)
                    show_kids = bool(kid_matches) or parent_match
                    kid_filter = kid_matches if (not parent_match) else None

                if not show_parent:
                    continue

                if is_parent:
                    pid = self.tree.insert(gid, "end", text=n, values=("",""))
                    self._tree_node_kind[pid] = "parent"
                    self._tree_node_name[pid] = n

                    # parent itself is a normal area too (we allow showing its rectangle)
                    add_area_node(pid, n)

                    kid_list = kids
                    if kid_filter is not None:
                        kid_list = kid_filter

                    for k in kid_list:
                        # slots as children
                        coords_offset = self.offset_area(self.data[k]["coords"])
                        vis = "✅" if self._is_visible(k) else ""
                        sid = self.tree.insert(pid, "end", text=k, values=(vis, str(coords_offset)))
                        self._tree_node_kind[sid] = "slot"
                        self._tree_node_name[sid] = k

                    # collapse heavy parents by default when not searching
                    if not q:
                        self.tree.item(pid, open=False)
                    else:
                        self.tree.item(pid, open=True)
                else:
                    if not matches(n):
                        continue
                    add_area_node(gid, n)

            # collapse groups by default (except when searching)
            self.tree.item(gid, open=bool(q))

        # refresh grid parent option menu (keep it sane)
        self._refresh_parent_menu()

    def _refresh_parent_menu(self):
        if not hasattr(self, "parent_menu"):
            return
        names = sorted(self.data.keys())
        menu = self.parent_menu["menu"]
        menu.delete(0, "end")
        for n in names:
            menu.add_command(label=n, command=lambda v=n: self.grid_parent_var.set(v))
        if names and self.grid_parent_var.get() not in names:
            self.grid_parent_var.set(names[0])

    def _get_tree_area_under_cursor(self, event):
        node = self.tree.identify_row(event.y)
        if not node:
            return None, None
        kind = self._tree_node_kind.get(node)
        name = self._tree_node_name.get(node)
        return kind, name

    def _toggle_node_visibility(self, node_id):
        kind = self._tree_node_kind.get(node_id)
        name = self._tree_node_name.get(node_id)

        # Toggle subtree for group or parent nodes
        if kind in {"group", "parent"}:
            # collect all descendant real areas
            descendants = []
            stack = [node_id]
            while stack:
                cur = stack.pop()
                for ch in self.tree.get_children(cur):
                    stack.append(ch)
                    ck = self._tree_node_kind.get(ch)
                    cn = self._tree_node_name.get(ch)
                    if ck in {"area", "slot"} and cn in self.data:
                        descendants.append(cn)

            # decide target state: if any hidden -> show all, else hide all
            any_hidden = any((d not in self.visible_areas) for d in descendants)
            target = True if any_hidden else False
            for d in descendants:
                self._set_visible(d, target)

        # Toggle a single area or slot
        elif kind in {"area", "slot"} and name in self.data:
            self._set_visible(name, not self._is_visible(name))

        self.draw_areas()
        self.rebuild_tree()

    def _select_node(self, node_id):
        kind = self._tree_node_kind.get(node_id)
        name = self._tree_node_name.get(node_id)

        # Click on parent/group does nothing special
        if kind in {"group"}:
            return

        # For parent node: select parent area
        if kind == "parent":
            if name in self.data:
                self.selected_area = name
                self._set_grid_parent(name)
                self.visible_areas.add(name)
                self.draw_areas()
            return

        # For area/slot: select it
        if kind in {"area", "slot"} and name in self.data:
            self.selected_area = name
            self._set_grid_parent(name)
            self.visible_areas.add(name)
            self.draw_areas()

    def _on_tree_click(self, event):
        node = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)  # "#1" is vis column
        if not node:
            return

        if col == "#1":
            self._toggle_node_visibility(node)
            return

        self._select_node(node)

    def _on_tree_double_click(self, event):
        node = self.tree.identify_row(event.y)
        if not node:
            return
        kind = self._tree_node_kind.get(node)
        if kind in {"area", "slot", "parent"}:
            name = self._tree_node_name.get(node)
            if name in self.data:
                self.prompt_rename(name)

    def _on_tree_right_click(self, event):
        node = self.tree.identify_row(event.y)
        if not node:
            return
        self._ctx_target_node = node
        kind = self._tree_node_kind.get(node)
        if kind in {"group"}:
            return
        self.ctx.tk_popup(event.x_root, event.y_root)

    def _ctx_area_name(self):
        if not self._ctx_target_node:
            return None
        kind = self._tree_node_kind.get(self._ctx_target_node)
        name = self._tree_node_name.get(self._ctx_target_node)
        if kind in {"area", "slot", "parent"} and name in self.data:
            return name
        return None

    def _ctx_rename(self):
        name = self._ctx_area_name()
        if name:
            self.prompt_rename(name)

    def _ctx_group(self):
        name = self._ctx_area_name()
        if name:
            self.prompt_group(name)

    def _ctx_delete(self):
        name = self._ctx_area_name()
        if name:
            self.delete_area(name)

    # ----------------------------
    # Add new area
    # ----------------------------
    def add_new_area(self):
        base = "NieuwGebied"
        i = 1
        while f"{base}_{i}" in self.data:
            i += 1
        name = f"{base}_{i}"

        self.data[name] = {"coords": [100, 100, 200, 200], "group": "default"}
        self.visible_areas.add(name)
        self._history_init(name)

        self.save_areas()
        self.draw_areas()
        self.rebuild_tree()
        print(f"🆕 Gebied '{name}' toegevoegd.")

if __name__ == "__main__":
    AreaOverlay().mainloop()
