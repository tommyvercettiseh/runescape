from __future__ import annotations

from typing import Callable, Optional, Iterable, Set, FrozenSet
import threading

try:
    from pynput import keyboard, mouse
except Exception as e:
    keyboard = None
    mouse = None
    _IMPORT_ERR = e
else:
    _IMPORT_ERR = None


def _norm_key(k) -> str:
    """
    Normalise pynput keys naar simpele strings:
    'ctrl', 'alt', 'shift', 'f8', 'f9', 's', 'd', 'x1', 'x2', etc.
    """
    # Special keys (Key.*)
    try:
        if isinstance(k, keyboard.Key):
            name = str(k).replace("Key.", "").lower()
            # unify some aliases
            if name in ("ctrl_l", "ctrl_r"):
                return "ctrl"
            if name in ("alt_l", "alt_r", "alt_gr"):
                return "alt"
            if name in ("shift_l", "shift_r"):
                return "shift"
            return name
    except Exception:
        pass

    # Character keys (KeyCode)
    try:
        if isinstance(k, keyboard.KeyCode) and k.char:
            return str(k.char).lower()
    except Exception:
        pass

    return ""


def _combo(*parts: str) -> FrozenSet[str]:
    return frozenset(p.strip().lower() for p in parts if p and p.strip())


class GlobalHotkeys:
    """
    Global hotkeys + mouse buttons, bedoeld voor "fysieke knoppen" die toetsen sturen.

    Voorbeelden combos:
      _combo("f8")
      _combo("ctrl", "alt", "s")
      _combo("shift", "f9")

    Mouse buttons:
      "x1" (back button), "x2" (forward button)
    """

    def __init__(
        self,
        on_direct: Callable[[], None],
        on_delayed: Callable[[], None],
        direct_combos: Iterable[FrozenSet[str]] = (_combo("f8"),),
        delayed_combos: Iterable[FrozenSet[str]] = (_combo("f9"),),
        direct_mouse_buttons: Iterable[str] = ("x1",),
        delayed_mouse_buttons: Iterable[str] = ("x2",),
    ):
        self.on_direct = on_direct
        self.on_delayed = on_delayed

        self.direct_combos = list(direct_combos)
        self.delayed_combos = list(delayed_combos)

        self.direct_mouse_buttons = set(b.lower() for b in direct_mouse_buttons)
        self.delayed_mouse_buttons = set(b.lower() for b in delayed_mouse_buttons)

        self._alive = False
        self._thread: Optional[threading.Thread] = None

        self._kb_listener: Optional["keyboard.Listener"] = None
        self._mouse_listener: Optional["mouse.Listener"] = None

        self._pressed: Set[str] = set()
        self._lock = threading.Lock()

    def start(self):
        if keyboard is None or mouse is None:
            raise RuntimeError(f"pynput import faalde: {_IMPORT_ERR}. Run: pip install pynput")
        if self._alive:
            return
        self._alive = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._alive = False
        try:
            if self._kb_listener is not None:
                self._kb_listener.stop()
        except Exception:
            pass
        try:
            if self._mouse_listener is not None:
                self._mouse_listener.stop()
        except Exception:
            pass
        self._kb_listener = None
        self._mouse_listener = None

    def _matches(self, combos: list[FrozenSet[str]]) -> bool:
        with self._lock:
            pressed = set(self._pressed)
        for c in combos:
            if c and c.issubset(pressed):
                return True
        return False

    def _run(self):
        def on_press(key):
            if not self._alive:
                return False
            k = _norm_key(key)
            if not k:
                return

            with self._lock:
                self._pressed.add(k)

            # Check combos
            try:
                if self._matches(self.direct_combos):
                    self.on_direct()
                elif self._matches(self.delayed_combos):
                    self.on_delayed()
            except Exception:
                pass

        def on_release(key):
            k = _norm_key(key)
            if not k:
                return
            with self._lock:
                self._pressed.discard(k)

        def on_click(x, y, button, pressed):
            if not self._alive:
                return False
            if not pressed:
                return

            bname = ""
            try:
                # mouse.Button.x1 / x2
                bname = str(button).replace("Button.", "").lower()
            except Exception:
                return

            try:
                if bname in self.direct_mouse_buttons:
                    self.on_direct()
                elif bname in self.delayed_mouse_buttons:
                    self.on_delayed()
            except Exception:
                pass

        self._kb_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._mouse_listener = mouse.Listener(on_click=on_click)

        self._kb_listener.start()
        self._mouse_listener.start()

        self._kb_listener.join()
        self._mouse_listener.join()