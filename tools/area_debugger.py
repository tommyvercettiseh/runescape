from __future__ import annotations

import json
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

# ============================================================
# BOOTSTRAP: project-root in sys.path
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bot_offsets import get_offset  # noqa: E402

# ============================================================
# FILES
# ============================================================
AREAS_FILE = ROOT / "config" / "areas.json"
AREAS_FILE.parent.mkdir(parents=True, exist_ok=True)
if not AREAS_FILE.exists():
    AREAS_FILE.write_text("{}", encoding="utf-8")

# ============================================================
# UI CONSTANTS
# ============================================================
HANDLE_SIZE = 8
HANDLE_OFFSET = 6
HANDLE_FILL = "#ffffff"
HANDLE_OUTLINE = "#333333"

MOVE_HANDLE_R = 14
MOVE_HANDLE_FILL = "#111111"
MOVE_HANDLE_OUTLINE = "#ffffff"


@dataclass
class AreaRec:
    coords: list[int]  # [x1,y1,x2,y2] base coords (no bot offset)
    group: str = "default"


class AreasUIv2(tk.Tk):
    """
    Areas editor (v2)
    ✅ Backwards compatible areas.json
      - old: "Name": [x1,y1,x2,y2]
      - new: "Name": {"coords":[...], "group":"..."}
    """

    def __init__(self):
        super().__init__()

        self.title("Areas UI v2")
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
        self.canvas.pack(fill="both", expand=True)

        # Bot offsets
        self.bot_id = 1
        self.x_offset, self.y_offset = get_offset(self.bot_id)

        # Data
        self.data: dict[str, AreaRec] = self._load_areas()
        self.visible_areas: set[str] = set(self.data.keys())  # current filter view
        self.active_group: str = "ALL"  # "ALL" means no filter

        # Selection / drag state
        self.selected_area: str | None = None
        self.active_handle: str | None = None
        self.drag_mode: str | None = None  # "move" | "resize"
        self.offset_x = 0
        self.offset_y = 0

        # Canvas ids
        self.rect_ids: dict[str, int] = {}
        self.label_ids: dict[str, int] = {}
        self.handle_ids: dict[str, dict[str, int]] = {}
        self.move_ids: dict[str, int] = {}

        # History (optional light)
        self.undo_stack: dict[str, list[list[int]]] = {}
        self.redo_stack: dict[str, list[list[int]]] = {}
        self._edit_started = False
        self._edit_area_name: str | None = None

        # Deleted stack (undo delete)
        self.deleted_stack: list[tuple[str, AreaRec]] = []

        # UI windows
        self._build_top_bot_selector()
        self._build_manager_window()

        # Draw
        self._apply_group_filter("ALL", redraw=False)
        self.draw_areas()

        # Bindings
        self.canvas.bind("<Button-1>", self.on_mouse_down_left)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag_left)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up_left)

        self.canvas.bind("<Double-Button-1>", self.on_double_click_canvas)
        self.bind("<Escape>", lambda e: self.destroy())

    # ============================================================
    # IO
    # ============================================================
    def _load_areas(self) -> dict[str, AreaRec]:
        try:
            raw = json.loads(AREAS_FILE.read_text(encoding="utf-8-sig") or "{}")
        except json.JSONDecodeError as e:
            print(f"⚠️ areas.json kapot: {e}")
            return {}

        out: dict[str, AreaRec] = {}
        for name, v in (raw or {}).items():
            if isinstance(v, list) and len(v) == 4:
                out[name] = AreaRec(coords=[int(x) for x in v], group="default")
            elif isinstance(v, dict) and isinstance(v.get("coords"), list) and len(v["coords"]) == 4:
                g = (v.get("group") or "default").strip() or "default"
                out[name] = AreaRec(coords=[int(x) for x in v["coords"]], group=g)
        return out

    def _save_areas(self):
        payload = {name: {"coords": rec.coords, "group": rec.group} for name, rec in self.data.items()}
        AREAS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("✅ opgeslagen: areas.json")

    # ============================================================
    # Helpers
    # ============================================================
    def offset_area(self, coords: list[int]) -> list[int]:
        x1, y1, x2, y2 = coords
        return [
            int(x1 + self.x_offset),
            int(y1 + self.y_offset),
            int(x2 + self.x_offset),
            int(y2 + self.y_offset),
        ]

    def color_for_name(self, name: str) -> str:
        """
        Stable bright color, ALWAYS valid #RRGGBB.
        """
        h = abs(hash(name))
        r = 128 + (h % 128)
        g = 128 + ((h >> 8) % 128)
        b = 128 + ((h >> 16) % 128)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _ensure_history(self, name: str):
        self.undo_stack.setdefault(name, [])
        self.redo_stack.setdefault(name, [])

    def _record_before_edit(self, name: str):
        if self._edit_started and self._edit_area_name == name:
            return
        self._ensure_history(name)
        self.undo_stack[name].append(list(self.data[name].coords))
        self.redo_stack[name].clear()
        self._edit_started = True
        self._edit_area_name = name

    # ============================================================
    # Bot selector (top-left)
    # ============================================================
    def _build_top_bot_selector(self):
        frame = tk.Frame(self, bg="black")
        frame.place(x=20, y=20)

        tk.Label(frame, text="Bot ID:", bg="black", fg="white").pack(side="left")

        self.bot_var = tk.IntVar(value=self.bot_id)
        for i in (1, 2, 3, 4):
            tk.Radiobutton(
                frame,
                text=str(i),
                variable=self.bot_var,
                value=i,
                command=lambda v=i: self.switch_bot(v),
                bg="black",
                fg="white",
                selectcolor="gray",
            ).pack(side="left")

    def switch_bot(self, new_id: int):
        self.bot_id = int(new_id)
        self.x_offset, self.y_offset = get_offset(self.bot_id)
        print(f"🔄 Bot {self.bot_id} offset=({self.x_offset},{self.y_offset})")
        self._refresh_area_table()
        self.draw_areas()

    # ============================================================
    # Manager window UI (groups + areas)
    # ============================================================
    def _build_manager_window(self):
        self.win = tk.Toplevel(self)
        self.win.title("Areas Manager (v2)")
        self.win.geometry(f"520x740+{self.winfo_screenwidth() - 560}+80")
        self.win.attributes("-topmost", True)
        self.win.resizable(True, True)

        # Search
        top = tk.Frame(self.win)
        top.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(top, text="Search").pack(side="left")
        self.search_var = tk.StringVar(value="")
        tk.Entry(top, textvariable=self.search_var, font=("Arial", 11)).pack(side="left", fill="x", expand=True, padx=8)

        # Buttons row
        btns = tk.Frame(self.win)
        btns.pack(fill="x", padx=10, pady=(0, 8))

        tk.Button(btns, text="🆕 New area", command=self.add_new_area).pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(btns, text="📄 Duplicate", command=self.duplicate_selected_area).pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(btns, text="🗑 Delete", command=self.delete_selected_area).pack(side="left", fill="x", expand=True)

        # Undo delete row
        ud = tk.Frame(self.win)
        ud.pack(fill="x", padx=10, pady=(0, 10))
        self.undo_delete_btn = tk.Button(ud, text="↩ Undo delete", command=self.undo_delete)
        self.undo_delete_btn.pack(side="left", fill="x", expand=True)
        self._refresh_undo_delete_btn()

        # Groups table
        gbox = tk.LabelFrame(self.win, text="Groups (klik = filter)")
        gbox.pack(fill="x", padx=10, pady=(0, 10))

        self.group_tree = ttk.Treeview(gbox, columns=("count",), show="tree headings", height=7)
        self.group_tree.heading("#0", text="Group")
        self.group_tree.heading("count", text="#")
        self.group_tree.column("count", width=60, anchor="center", stretch=False)
        self.group_tree.pack(fill="x", padx=8, pady=8)

        gbtn = tk.Frame(gbox)
        gbtn.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(gbtn, text="➕ New group", command=self.new_group).pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(gbtn, text="✏️ Rename", command=self.rename_group).pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(gbtn, text="👁 Show all", command=lambda: self._apply_group_filter("ALL")).pack(side="left", fill="x", expand=True)

        # Areas table
        abox = tk.LabelFrame(self.win, text="Areas in selected group")
        abox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.area_tree = ttk.Treeview(abox, columns=("group", "vis", "coords"), show="tree headings")
        self.area_tree.heading("#0", text="Name")
        self.area_tree.heading("group", text="Group")
        self.area_tree.heading("vis", text="👁")
        self.area_tree.heading("coords", text="Coords (offset)")
        self.area_tree.column("group", width=120, anchor="w", stretch=False)
        self.area_tree.column("vis", width=46, anchor="center", stretch=False)
        self.area_tree.column("coords", width=220, anchor="w", stretch=True)

        yscroll = ttk.Scrollbar(abox, orient="vertical", command=self.area_tree.yview)
        self.area_tree.configure(yscrollcommand=yscroll.set)
        self.area_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        yscroll.pack(side="right", fill="y", padx=(0, 8), pady=8)

        # Bottom row actions
        act = tk.Frame(self.win)
        act.pack(fill="x", padx=10, pady=(0, 10))

        tk.Button(act, text="✏️ Rename", command=self.rename_selected_area).pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(act, text="🧷 Change group", command=self.change_group_selected_area).pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(act, text="↩ Undo move/resize", command=self.undo_selected_area).pack(side="left", fill="x", expand=True)

        # Bindings
        self.group_tree.bind("<<TreeviewSelect>>", self._on_group_select)
        self.area_tree.bind("<Button-1>", self._on_area_click)
        self.area_tree.bind("<Double-Button-1>", self._on_area_double_click)
        self.search_var.trace_add("write", lambda *_: self._refresh_area_table())

        # Initial fill
        self._refresh_group_table(select_group="ALL")
        self._refresh_area_table()

    # ============================================================
    # Group logic
    # ============================================================
    def _group_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for rec in self.data.values():
            counts[rec.group] = counts.get(rec.group, 0) + 1
        return counts

    def _refresh_group_table(self, *, select_group: str | None = None):
        self.group_tree.delete(*self.group_tree.get_children())
        counts = self._group_counts()

        total = sum(counts.values())
        self.group_tree.insert("", "end", iid="ALL", text="(ALL)", values=(total,))

        for g in sorted(counts.keys(), key=lambda s: s.lower()):
            self.group_tree.insert("", "end", iid=g, text=g, values=(counts[g],))

        if select_group is None:
            select_group = self.active_group
        if select_group in self.group_tree.get_children(""):
            self.group_tree.selection_set(select_group)
            self.group_tree.see(select_group)

    def _on_group_select(self, _evt=None):
        sel = self.group_tree.selection()
        if not sel:
            return
        gid = sel[0]
        self._apply_group_filter(gid)

    def _apply_group_filter(self, group: str, *, redraw: bool = True):
        self.active_group = group or "ALL"

        if self.active_group == "ALL":
            self.visible_areas = set(self.data.keys())
        else:
            self.visible_areas = {n for n, r in self.data.items() if r.group == self.active_group}

        self._refresh_area_table()
        if redraw:
            self.draw_areas()

    def new_group(self):
        g = simpledialog.askstring("New group", "Groupnaam:", parent=self.win)
        if not g:
            return
        g = g.strip()
        if not g:
            return

        if messagebox.askyesno("Group", f"Group '{g}' gemaakt.\nWil je de geselecteerde area direct in deze group zetten?", parent=self.win):
            self._set_selected_area_group(g)
        self._refresh_group_table(select_group=g)
        self._apply_group_filter(g)

    def rename_group(self):
        if self.active_group in {"ALL"}:
            messagebox.showinfo("Group", "Selecteer eerst een echte group om te hernoemen.", parent=self.win)
            return
        old = self.active_group
        new = simpledialog.askstring("Rename group", f"Nieuwe naam voor '{old}':", parent=self.win)
        if not new:
            return
        new = new.strip()
        if not new or new == old:
            return

        for rec in self.data.values():
            if rec.group == old:
                rec.group = new

        self._save_areas()
        self._refresh_group_table(select_group=new)
        self._apply_group_filter(new)

    # ============================================================
    # Areas table / selection
    # ============================================================
    def _refresh_area_table(self):
        if not hasattr(self, "area_tree"):
            return

        q = (self.search_var.get() or "").strip().lower()

        self.area_tree.delete(*self.area_tree.get_children())
        names = sorted(self.visible_areas, key=lambda s: s.lower())

        def matches(n: str) -> bool:
            return (not q) or (q in n.lower())

        for n in names:
            if not matches(n):
                continue
            rec = self.data[n]
            coords_offset = self.offset_area(rec.coords)
            vis = "✅" if (n in self.visible_areas) else ""
            self.area_tree.insert("", "end", iid=n, text=n, values=(rec.group, vis, str(coords_offset)))

    def _on_area_click(self, event):
        node = self.area_tree.identify_row(event.y)
        col = self.area_tree.identify_column(event.x)

        if not node:
            return

        # Toggle visibility on 👁 column
        if col == "#3":
            if node in self.visible_areas:
                self.visible_areas.discard(node)
            else:
                self.visible_areas.add(node)
            self._refresh_area_table()
            self.draw_areas()
            return

        self.selected_area = node
        self.visible_areas.add(node)
        self.draw_areas()

    def _on_area_double_click(self, _event):
        sel = self.area_tree.selection()
        if not sel:
            return
        self.prompt_rename(sel[0])

    # ============================================================
    # Canvas drawing
    # ============================================================
    def draw_areas(self):
        self.canvas.delete("all")
        self.rect_ids.clear()
        self.label_ids.clear()
        self.handle_ids.clear()
        self.move_ids.clear()

        for name in sorted(self.data.keys(), key=lambda s: s.lower()):
            if name not in self.visible_areas:
                continue

            rec = self.data[name]
            x1, y1, x2, y2 = self.offset_area(rec.coords)
            color = self.color_for_name(name)

            rid = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline=color, width=3,
                tags=("area", name),
            )
            self.rect_ids[name] = rid

            label = f"{name} ({rec.group}) [Bot {self.bot_id}]"
            lid = self.canvas.create_text(
                x1 + 5, y1 - 16,
                text=label, anchor="nw",
                fill=color, font=("Arial", 12, "bold"),
                tags=("label", name),
            )
            self.label_ids[name] = lid

            self._draw_resize_handles(name, x1, y1, x2, y2)
            self._draw_move_handle(name, x1, y1, x2, y2)

    def _draw_resize_handles(self, name: str, x1: int, y1: int, x2: int, y2: int):
        pos = self._handle_positions(x1, y1, x2, y2)
        self.handle_ids[name] = {}
        for k, (cx, cy) in pos.items():
            hid = self.canvas.create_rectangle(
                cx - HANDLE_SIZE / 2, cy - HANDLE_SIZE / 2,
                cx + HANDLE_SIZE / 2, cy + HANDLE_SIZE / 2,
                fill=HANDLE_FILL, outline=HANDLE_OUTLINE,
                tags=("handle", name, f"handle-{k}"),
            )
            self.handle_ids[name][k] = hid

    def _draw_move_handle(self, name: str, x1: int, y1: int, x2: int, y2: int):
        """
        ✅ FIX: geen unicode icoontje meer (dat gaf '?' bij sommige fonts)
        Drag blijft werken via tag "movehandle"
        """
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        mid = self.canvas.create_oval(
            cx - MOVE_HANDLE_R, cy - MOVE_HANDLE_R,
            cx + MOVE_HANDLE_R, cy + MOVE_HANDLE_R,
            fill=MOVE_HANDLE_FILL,
            outline=MOVE_HANDLE_OUTLINE,
            width=2,
            tags=("movehandle", name),
        )
        self.move_ids[name] = mid

    def _handle_positions(self, x1, y1, x2, y2):
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

    # ============================================================
    # Hit tests
    # ============================================================
    def _hit_move_handle(self, x: int, y: int) -> str | None:
        pad = MOVE_HANDLE_R + 6
        items = self.canvas.find_overlapping(x - pad, y - pad, x + pad, y + pad)
        for it in items:
            tags = set(self.canvas.gettags(it))
            if "movehandle" in tags:
                for t in tags:
                    if t not in {"movehandle", "current"} and t in self.data:
                        return t
        return None

    def _hit_resize_handle(self, x: int, y: int) -> tuple[str | None, str | None]:
        pad = max(3, HANDLE_SIZE // 2 + 3)
        items = self.canvas.find_overlapping(x - pad, y - pad, x + pad, y + pad)
        for it in items:
            tags = set(self.canvas.gettags(it))
            if "handle" in tags:
                name = None
                pos = None
                for t in tags:
                    if t.startswith("handle-"):
                        pos = t.split("handle-", 1)[1]
                    elif t not in {"handle", "current"} and t in self.data:
                        name = t
                if name and pos:
                    return name, pos
        return None, None

    def _hit_area_inside(self, x: int, y: int) -> tuple[str | None, int, int]:
        for name in self.visible_areas:
            x1, y1, x2, y2 = self.offset_area(self.data[name].coords)
            if x1 <= x <= x2 and y1 <= y <= y2:
                return name, (x - x1), (y - y1)
        return None, 0, 0

    # ============================================================
    # Mouse logic
    # ============================================================
    def on_mouse_down_left(self, event):
        mh = self._hit_move_handle(event.x, event.y)
        if mh:
            self.selected_area = mh
            self.drag_mode = "move"
            x1, y1, x2, y2 = self.offset_area(self.data[mh].coords)
            self.offset_x = event.x - x1
            self.offset_y = event.y - y1
            self._record_before_edit(mh)
            return

        name, pos = self._hit_resize_handle(event.x, event.y)
        if name and pos:
            self.selected_area = name
            self.active_handle = pos
            self.drag_mode = "resize"
            self._record_before_edit(name)
            return

        name, dx, dy = self._hit_area_inside(event.x, event.y)
        if name:
            self.selected_area = name
            self.drag_mode = "move"
            self.offset_x = dx
            self.offset_y = dy
            self._record_before_edit(name)
            return

        self.selected_area = None
        self.drag_mode = None
        self.active_handle = None

    def on_mouse_drag_left(self, event):
        if not self.selected_area or not self.drag_mode:
            return
        if self.drag_mode == "move":
            self._apply_move(event.x, event.y)
        elif self.drag_mode == "resize" and self.active_handle:
            self._apply_resize(event.x, event.y)

    def on_mouse_up_left(self, _event):
        if self.selected_area:
            self._save_areas()
            self._refresh_area_table()
        self.selected_area = None
        self.drag_mode = None
        self.active_handle = None
        self._edit_started = False
        self._edit_area_name = None

    def _apply_move(self, x: int, y: int):
        name = self.selected_area
        if not name:
            return
        x1, y1, x2, y2 = self.data[name].coords
        w, h = x2 - x1, y2 - y1
        new_x1 = int(x - self.offset_x - self.x_offset)
        new_y1 = int(y - self.offset_y - self.y_offset)
        self.data[name].coords = [new_x1, new_y1, new_x1 + w, new_y1 + h]
        self.draw_areas()
        self._refresh_area_row(name)

    def _apply_resize(self, x: int, y: int):
        name = self.selected_area
        if not name or not self.active_handle:
            return
        x1, y1, x2, y2 = self.data[name].coords
        ex = int(x - self.x_offset)
        ey = int(y - self.y_offset)

        min_size = 20
        if "w" in self.active_handle:
            x1 = min(ex, x2 - min_size)
        if "e" in self.active_handle:
            x2 = max(ex, x1 + min_size)
        if "n" in self.active_handle:
            y1 = min(ey, y2 - min_size)
        if "s" in self.active_handle:
            y2 = max(ey, y1 + min_size)

        self.data[name].coords = [x1, y1, x2, y2]
        self.draw_areas()
        self._refresh_area_row(name)

    # ============================================================
    # Rename
    # ============================================================
    def on_double_click_canvas(self, event):
        target = None
        for name, lbl_id in self.label_ids.items():
            bx = self.canvas.bbox(lbl_id)
            if bx and bx[0] <= event.x <= bx[2] and bx[1] <= event.y <= bx[3]:
                target = name
                break

        if not target:
            target, _, _ = self._hit_area_inside(event.x, event.y)

        if target:
            self.prompt_rename(target)

    def prompt_rename(self, old_name: str):
        if old_name not in self.data:
            return
        new_name = simpledialog.askstring("Rename", f"Nieuwe naam voor '{old_name}':", parent=self.win)
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name:
            return
        if new_name in self.data and new_name != old_name:
            return messagebox.showerror("Bestaat al", f"'{new_name}' bestaat al.", parent=self.win)

        self.data[new_name] = self.data.pop(old_name)

        if old_name in self.undo_stack:
            self.undo_stack[new_name] = self.undo_stack.pop(old_name)
        if old_name in self.redo_stack:
            self.redo_stack[new_name] = self.redo_stack.pop(old_name)

        if old_name in self.visible_areas:
            self.visible_areas.discard(old_name)
            self.visible_areas.add(new_name)

        self._save_areas()
        self._refresh_group_table(select_group=self.active_group)
        self._refresh_area_table()
        self.draw_areas()
        self._select_area_in_table(new_name)

    # ============================================================
    # Area actions
    # ============================================================
    def _suggest_unique_name(self, base: str) -> str:
        base = (base or "NieuwGebied").strip() or "NieuwGebied"
        if base not in self.data:
            return base
        i = 2
        while f"{base}_{i}" in self.data:
            i += 1
        return f"{base}_{i}"

    def _default_group_for_new_area(self) -> str:
        if self.active_group and self.active_group != "ALL":
            return self.active_group
        return "default"

    def add_new_area(self):
        suggested = self._suggest_unique_name("NieuwGebied")
        name = simpledialog.askstring("New area", "Naam:", initialvalue=suggested, parent=self.win)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.data:
            return messagebox.showerror("Bestaat al", f"'{name}' bestaat al.", parent=self.win)

        g = self._default_group_for_new_area()
        self.data[name] = AreaRec(coords=[100, 100, 220, 200], group=g)
        self.visible_areas.add(name)
        self._ensure_history(name)

        self._save_areas()
        self._refresh_group_table(select_group=self.active_group)
        self._refresh_area_table()
        self.draw_areas()
        self._select_area_in_table(name)

    def _selected_area_name(self) -> str | None:
        sel = self.area_tree.selection()
        return sel[0] if sel else None

    def duplicate_selected_area(self):
        src = self._selected_area_name()
        if not src or src not in self.data:
            return messagebox.showinfo("Duplicate", "Selecteer eerst een area om te duplicaten.", parent=self.win)

        suggested = self._suggest_unique_name(f"{src}_copy")
        new_name = simpledialog.askstring("Duplicate", f"Nieuwe naam (copy van '{src}'):", initialvalue=suggested, parent=self.win)
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name:
            return
        if new_name in self.data:
            return messagebox.showerror("Bestaat al", f"'{new_name}' bestaat al.", parent=self.win)

        src_rec = self.data[src]
        self.data[new_name] = AreaRec(coords=list(src_rec.coords), group=src_rec.group)
        self.visible_areas.add(new_name)
        self._ensure_history(new_name)

        self._save_areas()
        self._refresh_group_table(select_group=self.active_group)
        self._refresh_area_table()
        self.draw_areas()
        self._select_area_in_table(new_name)

    def delete_selected_area(self):
        name = self._selected_area_name()
        if not name or name not in self.data:
            return
        if not messagebox.askyesno("Delete", f"'{name}' verwijderen?", parent=self.win):
            return

        rec = self.data.pop(name)
        self.deleted_stack.append((name, rec))
        self.visible_areas.discard(name)
        self.undo_stack.pop(name, None)
        self.redo_stack.pop(name, None)

        self._save_areas()
        self._refresh_group_table(select_group=self.active_group)
        self._refresh_area_table()
        self.draw_areas()
        self._refresh_undo_delete_btn()

    def undo_delete(self):
        if not self.deleted_stack:
            return
        name, rec = self.deleted_stack.pop()
        if name in self.data:
            name = self._suggest_unique_name(name)

        self.data[name] = rec
        if self.active_group == "ALL" or rec.group == self.active_group:
            self.visible_areas.add(name)

        self._ensure_history(name)
        self._save_areas()
        self._refresh_group_table(select_group=self.active_group)
        self._refresh_area_table()
        self.draw_areas()
        self._refresh_undo_delete_btn()

    def rename_selected_area(self):
        name = self._selected_area_name()
        if name:
            self.prompt_rename(name)

    def _set_selected_area_group(self, group: str):
        name = self._selected_area_name()
        if not name or name not in self.data:
            return
        self.data[name].group = (group or "default").strip() or "default"
        self._save_areas()
        self._refresh_group_table(select_group=self.active_group)
        self._apply_group_filter(self.active_group)

    def change_group_selected_area(self):
        name = self._selected_area_name()
        if not name or name not in self.data:
            return messagebox.showinfo("Group", "Selecteer eerst een area.", parent=self.win)

        current = self.data[name].group
        groups = sorted({r.group for r in self.data.values()} | {"default"}, key=lambda s: s.lower())
        msg = "Kies group:\n\n" + "\n".join(groups)
        g = simpledialog.askstring("Change group", msg, initialvalue=current, parent=self.win)
        if not g:
            return
        g = g.strip() or "default"
        self.data[name].group = g
        self._save_areas()

        self._refresh_group_table(select_group=self.active_group)
        self._apply_group_filter(self.active_group)

    def undo_selected_area(self):
        name = self._selected_area_name()
        if not name or name not in self.data:
            return
        self._ensure_history(name)
        if not self.undo_stack[name]:
            return

        cur = list(self.data[name].coords)
        prev = self.undo_stack[name].pop()
        self.redo_stack[name].append(cur)
        self.data[name].coords = prev
        self._save_areas()
        self._refresh_area_table()
        self.draw_areas()
        self._select_area_in_table(name)

    # ============================================================
    # Small UI helpers
    # ============================================================
    def _refresh_undo_delete_btn(self):
        if hasattr(self, "undo_delete_btn"):
            self.undo_delete_btn.configure(state=("normal" if self.deleted_stack else "disabled"))

    def _select_area_in_table(self, name: str):
        try:
            self.area_tree.selection_set(name)
            self.area_tree.see(name)
        except Exception:
            pass

    def _refresh_area_row(self, name: str):
        if not hasattr(self, "area_tree"):
            return
        if name not in self.area_tree.get_children(""):
            return
        rec = self.data[name]
        coords_offset = self.offset_area(rec.coords)
        self.area_tree.item(name, values=(rec.group, "✅", str(coords_offset)))


if __name__ == "__main__":
    AreasUIv2().mainloop()
