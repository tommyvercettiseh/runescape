from __future__ import annotations

import json
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

# ============================================================
# Paths (alles binnen tools/keyboard_lab)
# ============================================================
BASE_DIR = Path(__file__).resolve().parent  # .../tools/keyboard_lab
SESSIONS_DIR = BASE_DIR / "sessions"
MASTER_PROFILE_OUT = BASE_DIR / "master_profile.json"

# ============================================================
# Key classification
# ============================================================
PUNCT = set(r"""`~!@#$%^&*()-_=+[{]}\|;:'",<.>/?""")

MOD_KEYS = {"shift", "control", "alt", "meta"}
EDIT_KEYS = {"backspace", "delete"}
NAV_KEYS = {"up", "down", "left", "right", "home", "end", "page_up", "page_down", "insert"}
ENTER_KEYS = {"enter"}
SPACE_KEYS = {"space"}
TAB_KEYS = {"tab"}

def normalize_tk_key(event: tk.Event) -> str:
    """
    Normaliseert Tk keysym naar stabiele tokens.
    Belangrijk: modifiers links/rechts -> 1 naam.
    """
    k = (event.keysym or "").strip().lower()

    # enter
    if k in {"kp_enter", "return"}:
        return "enter"

    # paging
    if k == "prior":
        return "page_up"
    if k == "next":
        return "page_down"

    # escape
    if k == "escape":
        return "esc"

    # modifiers (L/R)
    if k in {"shift_l", "shift_r"}:
        return "shift"
    if k in {"control_l", "control_r"}:
        return "control"
    if k in {"alt_l", "alt_r"}:
        return "alt"

    # some tk variants
    if k == "space":
        return "space"

    return k

def key_class(k: str) -> str:
    if k in MOD_KEYS:
        return "mod"
    if k in EDIT_KEYS:
        return "edit"
    if k in NAV_KEYS:
        return "nav"
    if k in ENTER_KEYS:
        return "enter"
    if k in SPACE_KEYS:
        return "space"
    if k in TAB_KEYS:
        return "tab"

    if len(k) == 1 and k.isalpha():
        return "alpha"
    if len(k) == 1 and k.isdigit():
        return "digit"
    if len(k) == 1 and k in PUNCT:
        return "punct"

    if k.startswith("f") and k[1:].isdigit():
        return "func"

    return "other"

# ============================================================
# Stats helpers
# ============================================================
def pct(xs: List[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return float(s[f])
    return float(s[f] + (s[c] - s[f]) * (k - f))

def mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0

def summarize(xs: List[float]) -> dict:
    return {
        "n": len(xs),
        "mean": mean(xs),
        "p50": pct(xs, 50),
        "p75": pct(xs, 75),
        "p90": pct(xs, 90),
        "p95": pct(xs, 95),
        "p99": pct(xs, 99),
    }

# ============================================================
# Event model
# ============================================================
@dataclass
class KeyEvent:
    ts: float
    event: str          # "down" / "up"
    key: str            # normalized
    key_class: str
    is_modifier: bool

# ============================================================
# Recorder + Metrics
# ============================================================
class KeyboardSession:
    """
    WAT:
      Houdt raw events bij + realtime metrics die je nodig hebt
      om iemand later 1:1 te reconstrueren.

    WHY:
      Je ai_keyboard moet distributions kunnen nabootsen:
      hold per class, IKI, bursts, pauses, enter dwell, correction gedrag.
    """
    def __init__(self):
        self.events: List[KeyEvent] = []

        # holds
        self.down_ts: Dict[str, float] = {}
        self.holds_by_class: Dict[str, List[float]] = {}

        # rhythm
        self.iki_ms: List[float] = []
        self.event_gap_ms: List[float] = []
        self.last_up_ts: Optional[float] = None
        self.last_event_ts: Optional[float] = None

        # burst model
        self.burst_gap_threshold_ms: float = 250.0
        self.current_burst_len: int = 0
        self.burst_lengths: List[int] = []
        self.burst_gaps_ms: List[float] = []

        # enter dwell
        self.last_non_enter_down_ts: Optional[float] = None
        self.enter_dwell_ms: List[float] = []

        # corrections
        self.keypress_count = 0
        self.backspace_count = 0
        self.correction_chain_len: int = 0
        self.correction_chains: List[int] = []
        self.correction_start_ts: Optional[float] = None
        self.correction_time_ms: List[float] = []

    def add_event(self, ev: KeyEvent):
        self.events.append(ev)

        # global event gaps (pause model)
        if self.last_event_ts is not None:
            self.event_gap_ms.append((ev.ts - self.last_event_ts) * 1000.0)
        self.last_event_ts = ev.ts

        if ev.event == "down":
            self.down_ts[ev.key] = ev.ts
            self.keypress_count += 1

            # enter dwell (commit latency)
            if ev.key != "enter":
                self.last_non_enter_down_ts = ev.ts
            else:
                if self.last_non_enter_down_ts is not None:
                    self.enter_dwell_ms.append((ev.ts - self.last_non_enter_down_ts) * 1000.0)

            # IKI + burst logic
            if self.last_up_ts is not None:
                iki = (ev.ts - self.last_up_ts) * 1000.0
                self.iki_ms.append(iki)

                # burst segmentation
                if iki > self.burst_gap_threshold_ms:
                    # close previous burst
                    if self.current_burst_len > 0:
                        self.burst_lengths.append(self.current_burst_len)
                    self.current_burst_len = 1
                    self.burst_gaps_ms.append(iki)
                else:
                    self.current_burst_len = max(1, self.current_burst_len + 1)
            else:
                self.current_burst_len = 1

            # correction chain logic (backspace runs)
            if ev.key == "backspace":
                self.backspace_count += 1
                self.correction_chain_len += 1
                if self.correction_start_ts is None:
                    self.correction_start_ts = ev.ts
            else:
                # finalize correction chain if ended
                if self.correction_chain_len > 0:
                    self.correction_chains.append(self.correction_chain_len)
                    self.correction_chain_len = 0

                    if self.correction_start_ts is not None:
                        self.correction_time_ms.append((ev.ts - self.correction_start_ts) * 1000.0)
                        self.correction_start_ts = None

        elif ev.event == "up":
            self.last_up_ts = ev.ts
            t0 = self.down_ts.pop(ev.key, None)
            if t0 is not None:
                hold = (ev.ts - t0) * 1000.0
                self.holds_by_class.setdefault(ev.key_class, []).append(hold)

    def finalize(self):
        # close last burst
        if self.current_burst_len > 0:
            self.burst_lengths.append(self.current_burst_len)
            self.current_burst_len = 0

        # close correction chain if still open
        if self.correction_chain_len > 0:
            self.correction_chains.append(self.correction_chain_len)
            self.correction_chain_len = 0

        if self.correction_start_ts is not None:
            # we don't know exact end; use last event ts
            end_ts = self.last_event_ts if self.last_event_ts is not None else self.correction_start_ts
            self.correction_time_ms.append((end_ts - self.correction_start_ts) * 1000.0)
            self.correction_start_ts = None

    def build_session_profile(self) -> dict:
        self.finalize()

        holds_summary = {k: summarize(v) for k, v in self.holds_by_class.items()}
        iki_summary = summarize(self.iki_ms)
        gap_summary = summarize(self.event_gap_ms)
        burst_len_summary = summarize([float(x) for x in self.burst_lengths])
        burst_gap_summary = summarize(self.burst_gaps_ms)
        enter_summary = summarize(self.enter_dwell_ms)
        corr_chain_summary = summarize([float(x) for x in self.correction_chains])
        corr_time_summary = summarize(self.correction_time_ms)

        pauses = [g for g in self.event_gap_ms if g > self.burst_gap_threshold_ms]
        pause_ch = (len(pauses) / max(1, len(self.event_gap_ms))) if self.event_gap_ms else 0.08
        pause_ch = max(0.02, min(0.35, float(pause_ch)))

        # defaults mapping: engine gebruikt dit direct
        alpha = self.holds_by_class.get("alpha", [])
        alpha_p50 = pct(alpha, 50) if alpha else 70.0
        alpha_p90 = pct(alpha, 90) if alpha else 140.0

        behavior = {
            # micro press timing
            "press_min_s": 0.012,
            "press_max_s": 0.040,

            # typing rhythm (jouw IKI)
            "type_interval_min_s": max(0.012, min(0.060, (iki_summary["p50"] / 1000.0) * 0.55 if iki_summary["n"] else 0.020)),
            "type_interval_max_s": max(0.020, min(0.110, (iki_summary["p75"] / 1000.0) * 0.85 if iki_summary["n"] else 0.055)),

            # pause / burst
            "pause_chance": pause_ch,
            "pause_min_s": 0.14,
            "pause_max_s": 0.65,
            "burst_gap_ms": float(self.burst_gap_threshold_ms),
            "burst_len_p50": burst_len_summary["p50"],
            "burst_len_p90": burst_len_summary["p90"],
            "burst_gap_p50_ms": burst_gap_summary["p50"],
            "burst_gap_p90_ms": burst_gap_summary["p90"],

            # holds (global fallback)
            "hold_min_s": max(0.035, min(0.140, (alpha_p50 / 1000.0) * 0.85)),
            "hold_max_s": max(0.090, min(0.380, (alpha_p90 / 1000.0) * 1.10)),

            # corrections (jij)
            "backspace_per_100_keys": (self.backspace_count / max(1, self.keypress_count)) * 100.0,
            "correction_chain_p50": corr_chain_summary["p50"],
            "correction_chain_p90": corr_chain_summary["p90"],
            "correction_time_p50_ms": corr_time_summary["p50"],
            "correction_time_p90_ms": corr_time_summary["p90"],

            # enter behavior
            "enter_dwell_p50_ms": enter_summary["p50"],
            "enter_dwell_p90_ms": enter_summary["p90"],

            # keep taste
            "mistake_chance": 0.02,
            "mistake_fix_chance": 0.88,
            "force_lower_default": True,
        }

        return {
            "meta": {
                "created_ts": time.time(),
                "sample_events": len(self.events),
                "burst_gap_threshold_ms": self.burst_gap_threshold_ms,
            },
            "stats": {
                "keypress_count": self.keypress_count,
                "backspace_count": self.backspace_count,
                "backspace_per_100_keys": (self.backspace_count / max(1, self.keypress_count)) * 100.0,
                "holds_by_class_ms": holds_summary,
                "iki_ms": iki_summary,
                "event_gap_ms": gap_summary,
                "burst_len": burst_len_summary,
                "burst_gaps_ms": burst_gap_summary,
                "enter_dwell_ms": enter_summary,
                "correction_chains": corr_chain_summary,
                "correction_time_ms": corr_time_summary,
            },
            "behavior": behavior,
        }

# ============================================================
# Master builder (bundelt alle sessions uit sessions/*/events.jsonl)
# ============================================================
def _iter_event_files() -> List[Path]:
    if not SESSIONS_DIR.exists():
        return []
    return sorted(SESSIONS_DIR.glob("*/*events.jsonl"))

def _build_master_profile_from_files(files: List[Path]) -> dict:
    # We'll aggregate from raw events for stability
    s = KeyboardSession()

    # reset session-level state we don't want cross-session to chain too much
    s.last_up_ts = None
    s.last_event_ts = None
    s.current_burst_len = 0
    s.correction_chain_len = 0
    s.correction_start_ts = None

    for fp in files:
        with fp.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                ev = KeyEvent(
                    ts=float(e.get("ts", 0.0)),
                    event=str(e.get("event", "")),
                    key=str(e.get("key", "")),
                    key_class=str(e.get("key_class", "other")),
                    is_modifier=bool(e.get("is_modifier", False)),
                )

                # safeguard: enforce normalization & class again
                # (older logs might be messy)
                k = normalize_key_string(ev.key)
                cls = key_class(k)
                ev.key = k
                ev.key_class = cls
                ev.is_modifier = (cls == "mod")

                s.add_event(ev)

        # stop cross-session burst artifacts
        s.last_up_ts = None
        s.last_event_ts = None
        s.current_burst_len = 0
        s.correction_chain_len = 0
        s.correction_start_ts = None
        s.last_non_enter_down_ts = None

    prof = s.build_session_profile()
    prof["meta"]["source"] = "keyboard_lab master (raw events)"
    prof["meta"]["sessions"] = len(files)
    return prof

def normalize_key_string(k: str) -> str:
    """
    Normaliseert key strings uit oudere logs ook.
    """
    k = (k or "").strip().lower()

    if k in {"kp_enter", "return"}:
        return "enter"
    if k == "prior":
        return "page_up"
    if k == "next":
        return "page_down"
    if k == "escape":
        return "esc"
    if k in {"shift_l", "shift_r"}:
        return "shift"
    if k in {"control_l", "control_r"}:
        return "control"
    if k in {"alt_l", "alt_r"}:
        return "alt"
    return k

def build_and_write_master_profile() -> Optional[dict]:
    files = _iter_event_files()
    if not files:
        return None

    prof = _build_master_profile_from_files(files)
    MASTER_PROFILE_OUT.write_text(json.dumps(prof, indent=2, ensure_ascii=False), encoding="utf-8")
    return prof

# ============================================================
# UI App
# ============================================================
class KeyboardLabApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("⌨️ Keyboard Lab")
        self.root.geometry("960x680")
        self.root.minsize(900, 610)

        self.session = KeyboardSession()
        self.recording = False
        self.session_dir: Optional[Path] = None
        self.events_path: Optional[Path] = None
        self._writer_fp = None

        self._build_ui()
        self._bind_keys()

        self._tick_ui()

    def _build_ui(self):
        self.root.configure(bg="#111318")
        style = ttk.Style()
        style.theme_use("clam")

        top = tk.Frame(self.root, bg="#111318")
        top.pack(fill="x", padx=16, pady=14)

        self.status = tk.Label(top, text="Status: idle", fg="#b8c0cc", bg="#111318", font=("Segoe UI", 12, "bold"))
        self.status.pack(side="left")

        self.dot = tk.Label(top, text="●", fg="#444", bg="#111318", font=("Segoe UI", 14, "bold"))
        self.dot.pack(side="left", padx=10)

        btns = tk.Frame(top, bg="#111318")
        btns.pack(side="right")

        self.btn_start = tk.Button(btns, text="▶ Start", command=self.start, bg="#1f6feb", fg="white", relief="flat", padx=14, pady=8)
        self.btn_start.pack(side="left", padx=6)

        self.btn_stop = tk.Button(btns, text="⏹ Stop", command=self.stop, bg="#30363d", fg="white", relief="flat", padx=14, pady=8, state="disabled")
        self.btn_stop.pack(side="left", padx=6)

        self.btn_profile = tk.Button(btns, text="🧾 Save session + update master", command=self.save_and_update_master, bg="#2ea043", fg="white", relief="flat", padx=14, pady=8, state="disabled")
        self.btn_profile.pack(side="left", padx=6)

        mid = tk.Frame(self.root, bg="#111318")
        mid.pack(fill="both", expand=True, padx=16, pady=10)

        left = tk.Frame(mid, bg="#111318")
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(mid, bg="#111318")
        right.pack(side="right", fill="y", padx=(12, 0))

        tk.Label(left, text="Type hier (alleen dit venster wordt gemeten):", fg="#b8c0cc", bg="#111318", font=("Segoe UI", 11)).pack(anchor="w")
        self.text = tk.Text(
            left, height=14, bg="#0b0f14", fg="#e6edf3", insertbackground="#e6edf3",
            font=("Consolas", 13), relief="flat", padx=12, pady=12, wrap="word"
        )
        self.text.pack(fill="both", expand=True, pady=(8, 10))
        self.text.insert("end", "Tip: typ 3–10 min normaal. Gebruik ook backspace, enter, shift, cijfers, leestekens 😉\n")

        tk.Label(left, text="Live events (laatste 30):", fg="#b8c0cc", bg="#111318", font=("Segoe UI", 11)).pack(anchor="w")
        self.feed = tk.Listbox(left, height=8, bg="#0b0f14", fg="#c9d1d9", relief="flat")
        self.feed.pack(fill="x", pady=(8, 0))

        self.stat_title = tk.Label(right, text="Live stats", fg="#e6edf3", bg="#111318", font=("Segoe UI", 12, "bold"))
        self.stat_title.pack(anchor="w")

        self.stat_box = tk.Label(right, text="", justify="left", fg="#b8c0cc", bg="#111318", font=("Segoe UI", 10))
        self.stat_box.pack(anchor="w", pady=(8, 0))

        footer = tk.Label(self.root, text="ESC = stop • Focus moet in het tekstvak staan", fg="#6e7681", bg="#111318", font=("Segoe UI", 9))
        footer.pack(fill="x", padx=16, pady=(0, 10))

    def _bind_keys(self):
        self.text.bind("<KeyPress>", self._on_key_down, add=True)
        self.text.bind("<KeyRelease>", self._on_key_up, add=True)
        self.root.bind("<Escape>", lambda e: self.stop())

    def _open_writer(self):
        ts = time.strftime("%Y%m%d_%H%M%S")
        self.session_dir = SESSIONS_DIR / ts
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.session_dir / "events.jsonl"
        self._writer_fp = self.events_path.open("a", encoding="utf-8")

    def _write_event(self, ev: KeyEvent):
        if not self._writer_fp:
            return
        self._writer_fp.write(json.dumps(asdict(ev), ensure_ascii=False) + "\n")
        self._writer_fp.flush()

    def start(self):
        if self.recording:
            return
        self.session = KeyboardSession()
        self._open_writer()
        self.recording = True

        self.status.config(text=f"Status: recording → {self.session_dir.name}")
        self.dot.config(fg="#2ea043")
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_profile.config(state="disabled")

        self.text.focus_set()

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        self.session.finalize()

        try:
            if self._writer_fp:
                self._writer_fp.close()
        except Exception:
            pass
        self._writer_fp = None

        self.status.config(text="Status: stopped")
        self.dot.config(fg="#f85149")
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.btn_profile.config(state="normal")

    def save_and_update_master(self):
        if not self.session_dir or not self.events_path or not self.events_path.exists():
            messagebox.showerror("Geen data", "Geen session events gevonden.")
            return

        # write session profile beside events
        session_profile = self.session.build_session_profile()
        (self.session_dir / "session_profile.json").write_text(
            json.dumps(session_profile, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # update master
        master = build_and_write_master_profile()
        if master is None:
            messagebox.showwarning("Geen sessions", "Geen sessions gevonden om master te bouwen.")
            return

        messagebox.showinfo(
            "Saved ✅",
            f"Session:\n{self.session_dir / 'session_profile.json'}\n\nMaster:\n{MASTER_PROFILE_OUT}"
        )
        self.status.config(text=f"Status: master updated → {MASTER_PROFILE_OUT.name}")
        self.dot.config(fg="#a371f7")

    def _push_feed(self, line: str):
        self.feed.insert("end", line)
        if self.feed.size() > 30:
            self.feed.delete(0)
        self.feed.see("end")

    def _on_key_down(self, event: tk.Event):
        if not self.recording:
            return
        k = normalize_tk_key(event)
        cls = key_class(k)
        ev = KeyEvent(
            ts=time.time(),
            event="down",
            key=k,
            key_class=cls,
            is_modifier=(cls == "mod"),
        )
        self.session.add_event(ev)
        self._write_event(ev)
        self._push_feed(f"↓ {k:<12} [{cls}]")

    def _on_key_up(self, event: tk.Event):
        if not self.recording:
            return
        k = normalize_tk_key(event)
        cls = key_class(k)
        ev = KeyEvent(
            ts=time.time(),
            event="up",
            key=k,
            key_class=cls,
            is_modifier=(cls == "mod"),
        )
        self.session.add_event(ev)
        self._write_event(ev)
        self._push_feed(f"↑ {k:<12} [{cls}]")

    def _tick_ui(self):
        iki = self.session.iki_ms
        gaps = self.session.event_gap_ms
        bs100 = (self.session.backspace_count / max(1, self.session.keypress_count)) * 100.0

        alpha_holds = self.session.holds_by_class.get("alpha", [])
        mod_holds = self.session.holds_by_class.get("mod", [])
        edit_holds = self.session.holds_by_class.get("edit", [])
        enter_dw = self.session.enter_dwell_ms
        burst = [float(x) for x in self.session.burst_lengths]

        txt = []
        txt.append(f"Keys: {self.session.keypress_count}")
        txt.append(f"Backspace: {self.session.backspace_count} ({bs100:.1f}/100)")
        txt.append("")
        txt.append(f"IKI p50: {pct(iki,50):.0f} ms   p90: {pct(iki,90):.0f} ms")
        txt.append(f"Gap p50: {pct(gaps,50):.0f} ms   p90: {pct(gaps,90):.0f} ms")
        txt.append("")
        txt.append(f"Burst p50: {pct(burst,50):.0f}   p90: {pct(burst,90):.0f}   thr: {self.session.burst_gap_threshold_ms:.0f}ms")
        txt.append(f"Enter dwell p50: {pct(enter_dw,50):.0f} ms   p90: {pct(enter_dw,90):.0f} ms")
        txt.append("")
        txt.append(f"Hold alpha p50: {pct(alpha_holds,50):.0f} ms   p90: {pct(alpha_holds,90):.0f} ms")
        txt.append(f"Hold mod   p50: {pct(mod_holds,50):.0f} ms   p90: {pct(mod_holds,90):.0f} ms")
        txt.append(f"Hold edit  p50: {pct(edit_holds,50):.0f} ms   p90: {pct(edit_holds,90):.0f} ms")
        txt.append("")
        txt.append(f"Session: {self.session_dir.name if self.session_dir else '-'}")
        txt.append(f"Recording: {'YES' if self.recording else 'no'}")
        txt.append(f"Master: {MASTER_PROFILE_OUT.name if MASTER_PROFILE_OUT.exists() else '(nog niet)'}")

        self.stat_box.config(text="\n".join(txt))
        self.root.after(120, self._tick_ui)

# ============================================================
# Main
# ============================================================
def main():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    app = KeyboardLabApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()