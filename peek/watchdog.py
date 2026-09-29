"""Freeze detector for the UI thread.

A timer ticks on the UI thread and a background thread watches the ticks. When
the ticks stop, the watcher writes what the UI thread is executing to the log
while the window is still frozen, so a "not responding" report can be traced to
the call that blocked it.
"""
import logging
import sys
import threading
import time
import traceback

from PySide6.QtCore import QObject, QTimer

_log = logging.getLogger('rfab_viewer')

_TICK_MS = 250
_CHECK_SECS = 0.5
# Seconds blocked at which the stack is written. Windows marks the window
# "not responding" and offers to close the program at about 5.
_REPORT_AT = (2, 5, 15, 30, 60, 120, 300, 600)


def _pick_clock():
    """Monotonic seconds that do not advance while the computer sleeps, so
    waking the laptop is not reported as a freeze."""
    if sys.platform == "win32":
        try:
            import ctypes
            ticks = ctypes.c_ulonglong()
            query = ctypes.windll.kernel32.QueryUnbiasedInterruptTime
            if query(ctypes.byref(ticks)):
                def awake_seconds():
                    query(ctypes.byref(ticks))
                    return ticks.value / 1e7
                return awake_seconds
        except Exception:
            pass
    return time.monotonic


_awake_seconds = _pick_clock()


def _describe_windows():
    """What each open viewer window is showing. Reads plain Python attributes
    only: this runs off the UI thread, where Qt objects must not be touched."""
    from peek.resizable import ResizeMixin
    parts = []
    for w in list(ResizeMixin._all_viewers):
        try:
            cells = getattr(w, 'file_paths', None)  # GridView
            if cells is not None:
                where = f"{len(cells)} cells in {cells[0].parent}" if cells else "empty"
            else:
                files = getattr(w, '_file_list', None) or []
                idx = getattr(w, '_current_index', 0)
                if 0 <= idx < len(files):
                    where = f"{files[idx]}, {len(files)} in folder"
                else:
                    where = "still loading"
            parts.append(f"{type(w).__name__}[{where}]")
        except Exception:
            parts.append(type(w).__name__)
    return ", ".join(parts) or "none"


class FreezeWatchdog(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ui_thread = threading.get_ident()
        self._last_tick = _awake_seconds()
        self._reports = 0  # stack dumps written for the freeze in progress
        self._stop = threading.Event()
        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)

    def start(self):
        # The watcher runs from here, before the event loop does, so a viewer
        # that blocks while opening is caught too.
        self._last_tick = _awake_seconds()
        self._timer.start()
        threading.Thread(target=self._watch, name="freeze-watchdog", daemon=True).start()

    def stop(self):
        self._stop.set()

    def _tick(self):
        now = _awake_seconds()
        blocked = now - self._last_tick
        self._last_tick = now
        self._reports = 0
        if blocked >= _REPORT_AT[0]:
            _log.warning(f"FREEZE ended: UI thread was blocked for {blocked:.1f}s")

    def _watch(self):
        while not self._stop.wait(_CHECK_SECS):
            blocked = _awake_seconds() - self._last_tick
            n = self._reports
            if n >= len(_REPORT_AT) or blocked < _REPORT_AT[n]:
                continue
            self._reports = n + 1
            try:
                frame = sys._current_frames().get(self._ui_thread)
                stack = "".join(traceback.format_stack(frame)) if frame else "  (no Python frame)\n"
                _log.warning(
                    f"FREEZE: UI thread not responding for {blocked:.1f}s. "
                    f"Open windows: {_describe_windows()}. It is executing:\n{stack.rstrip()}"
                )
            except Exception as e:
                _log.warning(f"FREEZE: UI thread not responding for {blocked:.1f}s (stack unavailable: {e})")
