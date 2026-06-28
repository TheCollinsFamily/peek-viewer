from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu


class BossKey(QObject):
    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hidden = False
        self._managed_windows = []
        self._window_states = {}

    def register_window(self, window):
        if window not in self._managed_windows:
            self._managed_windows.append(window)
            try:
                window.destroyed.connect(lambda: self._remove_window(window))
            except (RuntimeError, AttributeError):
                pass

    def unregister_window(self, window):
        self._remove_window(window)

    def _remove_window(self, window):
        if window in self._managed_windows:
            self._managed_windows.remove(window)
        self._window_states.pop(id(window), None)

    def toggle(self):
        if self._hidden:
            self.show_all()
        else:
            self.hide_all()

    def hide_all(self):
        self._hidden = True
        self._window_states.clear()

        for win in list(self._managed_windows):
            try:
                self._window_states[id(win)] = win.isVisible()
                win.hide()
            except RuntimeError:
                self._managed_windows.remove(win)

        self.toggled.emit(True)

    def show_all(self):
        self._hidden = False

        for win in list(self._managed_windows):
            try:
                was_visible = self._window_states.get(id(win), True)
                if was_visible:
                    win.show()
                    win.raise_()
                    win.activateWindow()
            except RuntimeError:
                self._managed_windows.remove(win)

        self._window_states.clear()
        self.toggled.emit(False)

    @property
    def is_hidden(self):
        return self._hidden
