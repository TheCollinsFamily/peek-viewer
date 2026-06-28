import shiboken6
import logging
_log = logging.getLogger('rfab_viewer')

from PySide6.QtCore import Qt, QPoint, QRect, QEvent, Signal, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QPushButton, QWidget, QFrame, QApplication, QLabel

EDGE_SIZE = 20

_EDGE_NONE = 0
_EDGE_LEFT = 1
_EDGE_RIGHT = 2
_EDGE_TOP = 4
_EDGE_BOTTOM = 8


def _detect_edge(widget, pos):
    rect = widget.rect()
    edge = _EDGE_NONE
    if pos.x() <= EDGE_SIZE:
        edge |= _EDGE_LEFT
    elif pos.x() >= rect.width() - EDGE_SIZE:
        edge |= _EDGE_RIGHT
    if pos.y() <= EDGE_SIZE:
        edge |= _EDGE_TOP
    elif pos.y() >= rect.height() - EDGE_SIZE:
        edge |= _EDGE_BOTTOM
    return edge


def _cursor_for_edge(edge):
    if edge in (_EDGE_LEFT, _EDGE_RIGHT):
        return Qt.CursorShape.SizeHorCursor
    if edge in (_EDGE_TOP, _EDGE_BOTTOM):
        return Qt.CursorShape.SizeVerCursor
    if edge in (_EDGE_LEFT | _EDGE_TOP, _EDGE_RIGHT | _EDGE_BOTTOM):
        return Qt.CursorShape.SizeFDiagCursor
    if edge in (_EDGE_RIGHT | _EDGE_TOP, _EDGE_LEFT | _EDGE_BOTTOM):
        return Qt.CursorShape.SizeBDiagCursor
    return Qt.CursorShape.ArrowCursor


_WC_BTN_STYLE = """
    QPushButton {
        background: rgba(0, 0, 0, 0.45);
        color: rgba(255, 255, 255, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 4px;
        font-size: 14px;
        padding: 0;
    }
    QPushButton:hover {
        background: rgba(0, 0, 0, 0.65);
        color: white;
        border-color: rgba(255, 255, 255, 0.5);
    }
"""
_WC_MUTE_STYLE = """
    QPushButton {
        background: rgba(255, 255, 255, 0.06);
        color: rgba(255, 255, 255, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 4px;
        font-size: 14px;
        padding: 0;
        text-decoration: line-through;
    }
    QPushButton:hover {
        background: rgba(255, 255, 255, 0.15);
        color: rgba(255, 255, 255, 0.5);
        border-color: rgba(255, 255, 255, 0.25);
        text-decoration: line-through;
    }
"""
_WC_CLOSE_STYLE = """
    QPushButton {
        background: rgba(255, 255, 255, 0.06);
        color: rgba(255, 255, 255, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 4px;
        font-size: 14px;
        padding: 0;
    }
    QPushButton:hover {
        background: rgba(220, 50, 50, 0.6);
        color: rgba(255, 255, 255, 0.9);
        border-color: rgba(220, 50, 50, 0.5);
    }
"""


class _ButtonBar(QWidget):
    """Transparent floating overlay that renders above native video surfaces."""

    def __init__(self, parent_window):
        super().__init__()
        self._pw = parent_window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet("background: transparent;")

    def reposition(self):
        pw = self._pw
        if not shiboken6.isValid(pw):
            return
        if not pw._wc_buttons:
            return
        btn_count = len(pw._wc_buttons)
        bar_w = 28 * btn_count + 4 * (btn_count - 1) + 20
        bar_h = 48
        self.setFixedSize(bar_w, bar_h)

        try:
            geo = pw.geometry()
        except RuntimeError:
            return
        self.move(geo.x() + geo.width() - bar_w, geo.y())

        x = bar_w - 10
        for btn in reversed(pw._wc_buttons):
            x -= btn.width()
            btn.move(x, 10)
            x -= 4

    def eventFilter(self, obj, event):
        if not shiboken6.isValid(obj):
            return False
        try:
            t = event.type()
            if t in (QEvent.Type.Move, QEvent.Type.Resize):
                # Skip reposition during active drag (prevents crash on screen transitions)
                pw = self._pw
                if shiboken6.isValid(pw) and getattr(pw, '_move_drag_start', None) is not None:
                    return False
                if not obj.isMinimized():
                    self.reposition()
            elif t == QEvent.Type.Close:
                self.close()
            elif t == QEvent.Type.Show:
                self.reposition()
                self.show()
                self.raise_()
            elif t == QEvent.Type.Hide:
                self.hide()
            elif t == QEvent.Type.WindowActivate:
                self.reposition()
                self.show()
                self.raise_()
            elif t == QEvent.Type.WindowDeactivate:
                self.hide()
            elif t == QEvent.Type.WindowStateChange:
                if obj.isMinimized():
                    self.hide()
                elif obj.isVisible():
                    self.reposition()
                    self.show()
                    self.raise_()
        except RuntimeError:
            return False
        return False


class _MergeHighlight(QWidget):
    """Floating transparent overlay that shows a blue glow on merge targets."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(
            "background: rgba(88, 166, 255, 0.12); "
            "border: 3px solid rgba(88, 166, 255, 0.8); "
            "border-radius: 6px;"
        )
        self.hide()

    def cover_window(self, target_widget):
        geo = target_widget.geometry()
        self.setGeometry(geo)
        self.show()
        self.raise_()


class _GrabHandle(QLabel):
    """Visual drag handle - directly drags the parent window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText('\u2630')
        self.setFixedSize(28, 28)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            'QLabel { color: rgba(255,255,255,0.25); font-size: 14px; '
            'background: rgba(255,255,255,0.06); '
            'border: 1px solid rgba(255,255,255,0.08); '
            'border-radius: 4px; }'
            'QLabel:hover { color: rgba(255,255,255,0.7); '
            'background: rgba(255,255,255,0.15); '
            'border-color: rgba(255,255,255,0.25); }'
        )
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_start = None
        self._win_start = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._drag_start = event.globalPosition().toPoint()
            win = self.window()
            self._win_start = win.pos() if win else None
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_start and self._win_start:
            # Safety: if no buttons are held, cancel drag
            if not event.buttons() & Qt.MouseButton.LeftButton:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
                self._drag_start = None
                self._win_start = None
                event.accept()
                return
            delta = event.globalPosition().toPoint() - self._drag_start
            win = self.window()
            if win:
                win.move(self._win_start + delta)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_start = None
        self._win_start = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        event.accept()


class ResizeMixin:
    """Mixin that adds edge-resize and title-bar-free window dragging to frameless widgets.

    Subclasses must call `_resize_init()` in __init__ after super().__init__().
    Mouse handlers should call the _resize_* helpers and check return values
    to decide whether to handle the event themselves.
    """

    _all_viewers = []  # class-level registry of open viewer windows

    _merge_overlay = None  # shared singleton overlay

    def _resize_init(self):
        self._resize_edge = _EDGE_NONE
        self._resize_start_pos = None
        self._resize_start_geo = None
        self._move_drag_start = None
        self._merge_target = None
        self._wc_buttons = []
        self._btn_bar = None
        self._current_screen = None
        self._screen_transition_pending = False
        self._no_button_count = 0  # grace counter for drag safety
        self.setMouseTracking(True)
        ResizeMixin._all_viewers.append(self)
        if ResizeMixin._merge_overlay is None:
            ResizeMixin._merge_overlay = _MergeHighlight()
        # Track initial screen
        try:
            self._current_screen = self.screen()
        except Exception:
            self._current_screen = QApplication.primaryScreen()
        # Connect screenChanged signal after first show (windowHandle needs show)
        self._screen_transitioning = False

    def _on_screen_changed_live(self, new_screen):
        """Called in real-time when Qt detects the window moved to a new screen.
        This fires DURING the drag, before the DPI resize causes problems."""
        import time
        now = time.time()
        # Cooldown: ignore screen changes within 2 seconds of last transition
        if now - self._screen_transition_cooldown < 0.5:
            _log.info("SCREEN TRANSITION: BLOCKED by cooldown")
            return
        if self._screen_transitioning:
            _log.info("SCREEN TRANSITION: BLOCKED - already transitioning")
            return
        _log.info(f"SCREEN TRANSITION: detected move to {new_screen.name() if new_screen else '?'}")
        self._screen_transitioning = True

        # 1. Cancel any active drag immediately
        was_dragging = self._move_drag_start is not None
        self._move_drag_start = None
        self._resize_edge = _EDGE_NONE
        self._resize_start_pos = None
        self._resize_start_geo = None

        # Temporarily disconnect signal to prevent re-firing during settle
        try:
            wh = self.windowHandle()
            if wh:
                wh.screenChanged.disconnect(self._on_screen_changed_live)
        except Exception:
            pass

        # 2. Hide all content - go black
        for child in self.findChildren(QWidget):
            if child is not self._grab_handle:
                child.hide()
        if self._btn_bar:
            self._btn_bar.hide()

        # 3. After Qt settles the DPI change, snap to new screen and restore
        QTimer.singleShot(600, lambda: self._finish_screen_transition(new_screen))

    def _create_fullscreen_btn(self):
        # Grab handle for window dragging
        self._grab_handle = _GrabHandle(self)
        self._grab_handle.move(12, 6)
        self._grab_handle.raise_()
        _log.debug("INIT: grab handle created")
        _log.debug("INIT: creating button bar")
        self._btn_bar = _ButtonBar(self)
        _log.debug("INIT: button bar created")
        self.installEventFilter(self._btn_bar)
        # Set maximum size to prevent DPI-transition crash (8K limit)
        self.setMaximumSize(7680, 4320)
        self._wc_buttons = []
        self._mute_btn = None

        home_btn = QPushButton("⌂", self._btn_bar)
        home_btn.setFixedSize(28, 28)
        home_btn.setStyleSheet(_WC_BTN_STYLE)
        home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        home_btn.clicked.connect(self._on_home_clicked)
        self._wc_buttons.append(home_btn)

        mute_btn = QPushButton("♪", self._btn_bar)
        mute_btn.setFixedSize(28, 28)
        mute_btn.setStyleSheet(_WC_MUTE_STYLE)
        mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mute_btn.clicked.connect(self._on_mute_clicked)
        self._mute_btn = mute_btn
        self._wc_buttons.append(mute_btn)

        minimize_btn = QPushButton("—", self._btn_bar)
        minimize_btn.setFixedSize(28, 28)
        minimize_btn.setStyleSheet(_WC_BTN_STYLE)
        minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        minimize_btn.clicked.connect(self._on_minimize_clicked)
        self._wc_buttons.append(minimize_btn)

        fs_btn = QPushButton("⛶", self._btn_bar)
        fs_btn.setFixedSize(28, 28)
        fs_btn.setStyleSheet(_WC_BTN_STYLE)
        fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        self._wc_buttons.append(fs_btn)

        close_btn = QPushButton("✕", self._btn_bar)
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(_WC_CLOSE_STYLE)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        self._wc_buttons.append(close_btn)

        self._btn_bar.reposition()
        self._btn_bar.show()

    def _on_home_clicked(self):
        for w in QApplication.topLevelWidgets():
            if w.__class__.__name__ == 'LauncherWindow':
                w.show()
                w.raise_()
                w.activateWindow()
                break

    def _on_minimize_clicked(self):
        if self._btn_bar:
            self._btn_bar.hide()
        self.showMinimized()

    def _on_mute_clicked(self):
        if hasattr(self, '_audio') and self._audio:
            muted = not self._audio.isMuted()
            self._audio.setMuted(muted)
            if self._mute_btn:
                self._mute_btn.setText("♪" if muted else "♪")
                self._mute_btn.setStyleSheet(_WC_MUTE_STYLE if muted else _WC_BTN_STYLE)

    def _raise_grab_handle(self):
        if hasattr(self, "_grab_handle") and self._grab_handle:
            try:
                self._grab_handle.raise_()
            except RuntimeError:
                pass

    def _reposition_fs_btn(self):
        if self._btn_bar:
            self._btn_bar.reposition()

    def _is_left_button_held(self, event):
        """Check if left button is held using both event and global state (Windows workaround)."""
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._no_button_count = 0
            return True
        # Fallback: check global mouse button state (more reliable on Windows)
        if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:
            self._no_button_count = 0
            return True
        # Grace period: allow up to 3 consecutive no-button events before cancelling
        self._no_button_count += 1
        if self._no_button_count < 4:
            return True
        return False

    def _resize_mouse_move(self, event):
        """Call from mouseMoveEvent. Returns True if the event was consumed (resize/move in progress)."""
        if self._resize_edge != _EDGE_NONE and self._resize_start_pos is not None:
            # Safety: if left button no longer held, cancel resize
            if not self._is_left_button_held(event):
                _log.warning('DRAG SAFETY: resize cancelled - no left button in move event')
                self._resize_edge = _EDGE_NONE
                self._resize_start_pos = None
                self._resize_start_geo = None
                self._no_button_count = 0
                return True
            self._do_resize(event.globalPosition().toPoint())
            return True

        if self._move_drag_start is not None:
            # Safety: if left button no longer held, cancel drag
            if not self._is_left_button_held(event):
                _log.warning('DRAG SAFETY: move_drag cancelled - no left button in move event')
                self._move_drag_start = None
                self._resize_start_geo = None
                self._resize_edge = _EDGE_NONE
                self._no_button_count = 0
                if self._btn_bar:
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(50, self._safe_reshow_btn_bar)
                return True
            delta = event.globalPosition().toPoint() - self._move_drag_start
            self.move(self._resize_start_geo.topLeft() + delta)
            # Hide button bar and floating overlays during drag to prevent cross-screen crash
            if self._btn_bar and self._btn_bar.isVisible():
                _log.debug("DRAG: hiding btn_bar and floating overlays")
                self._btn_bar.hide()
            # Hide floating remove buttons (video cells in GridView)
            if hasattr(self, '_cells'):
                for c in self._cells:
                    if getattr(c, '_remove_btn_floating', False) and c._remove_btn.isVisible():
                        c._remove_btn.hide()
            self._check_merge_overlap()
            return True

        edge = _detect_edge(self, event.position().toPoint())
        if edge != _EDGE_NONE:
            self.setCursor(_cursor_for_edge(edge))
        else:
            self.unsetCursor()
        return False

    def _check_merge_overlap(self):
        """During drag, highlight any other viewer we overlap significantly."""
        my_geo = self.geometry()
        best = None
        best_area = 0
        for w in ResizeMixin._all_viewers:
            if w is self or not w.isVisible():
                continue
            other_geo = w.geometry()
            overlap = my_geo.intersected(other_geo)
            if not overlap.isEmpty():
                area = overlap.width() * overlap.height()
                # Require at least 10% overlap of the smaller window
                min_area = min(my_geo.width() * my_geo.height(),
                               other_geo.width() * other_geo.height())
                if area > min_area * 0.1 and area > best_area:
                    best = w
                    best_area = area

        # Update highlight overlay
        self._merge_target = best
        overlay = ResizeMixin._merge_overlay
        if overlay:
            if best:
                overlay.cover_window(best)
            else:
                overlay.hide()

    _DRAG_ZONE_HEIGHT = 50

    def _edge_to_qt_edges(self, edge):
        """Convert internal edge flags to Qt.Edge flags for startSystemResize."""
        from PySide6.QtCore import Qt as _Qt
        edges = _Qt.Edge(0)
        if edge & _EDGE_LEFT:
            edges |= _Qt.Edge.LeftEdge
        if edge & _EDGE_RIGHT:
            edges |= _Qt.Edge.RightEdge
        if edge & _EDGE_TOP:
            edges |= _Qt.Edge.TopEdge
        if edge & _EDGE_BOTTOM:
            edges |= _Qt.Edge.BottomEdge
        return edges

    def _resize_mouse_press(self, event):
        """Call from mousePressEvent. Returns True if a resize or move drag started."""
        if event.button() != Qt.MouseButton.LeftButton:
            return False

        pos = event.position().toPoint()
        edge = _detect_edge(self, pos)

        if edge != _EDGE_NONE:
            # Use native OS resize - much more reliable than manual tracking
            wh = self.windowHandle()
            if wh:
                qt_edges = self._edge_to_qt_edges(edge)
                _log.info(f'SYSTEM RESIZE: edge={edge} qt_edges={qt_edges}')
                wh.startSystemResize(qt_edges)
                return True
            # Fallback to manual resize if windowHandle not available
            self._resize_edge = edge
            self._resize_start_pos = event.globalPosition().toPoint()
            self._resize_start_geo = self.geometry()
            return True

        # Top drag zone acts like a title bar - use native move
        if pos.y() <= self._DRAG_ZONE_HEIGHT:
            wh = self.windowHandle()
            if wh:
                _log.info(f'SYSTEM MOVE: pos={pos.x()},{pos.y()}')
                wh.startSystemMove()
                return True
            # Fallback to manual move
            self._move_drag_start = event.globalPosition().toPoint()
            self._resize_start_geo = self.geometry()
            _log.info(f'DRAG START: pos={pos.x()},{pos.y()}')
            return True

        return False

    def _resize_mouse_release(self, event):
        """Call from mouseReleaseEvent. Returns True if a resize/move ended."""
        if event.button() == Qt.MouseButton.LeftButton:
            was_active = (self._resize_edge != _EDGE_NONE) or (self._move_drag_start is not None)
            was_moving = self._move_drag_start is not None
            if was_active:
                import logging
                logging.getLogger('rfab_viewer').info(
                    f'DRAG END: was_moving={was_moving}')
            merge_target = self._merge_target

            self._resize_edge = _EDGE_NONE
            self._resize_start_pos = None
            self._resize_start_geo = None
            self._move_drag_start = None
            self._merge_target = None

            # Clear highlight overlay
            if ResizeMixin._merge_overlay:
                ResizeMixin._merge_overlay.hide()

            # Trigger merge
            if was_moving and merge_target:
                self._do_merge(merge_target)
                return True

            # After drag, check if we landed on a different screen
            if was_moving:
                self._handle_screen_change_after_drag()
            else:
                # Re-show button bar after resize
                if self._btn_bar:
                    QTimer.singleShot(50, self._safe_reshow_btn_bar)

            return was_active
        return False

    def _handle_screen_change_after_drag(self):
        """After a drag ends, detect screen change and auto-fit to new screen."""
        _log.info("SCREEN CHECK: detecting screen after drag")
        try:
            new_screen = self.screen()
        except (RuntimeError, AttributeError):
            _log.warning("SCREEN CHECK: failed to get screen (RuntimeError)")
            new_screen = None

        if new_screen and new_screen != self._current_screen:
            _log.info(f"SCREEN CHANGE: {self._current_screen} -> {new_screen.name()} "
                      f"geo={new_screen.availableGeometry()}")
            # Screen changed — auto-fit to new screen
            self._current_screen = new_screen
            avail = new_screen.availableGeometry()
            geo = self.geometry()
            # If window is larger than 92% of new screen, resize to fit
            max_w = int(avail.width() * 0.92)
            max_h = int(avail.height() * 0.92)
            new_w = min(geo.width(), max_w)
            new_h = min(geo.height(), max_h)
            # Center on the new screen
            x = avail.x() + (avail.width() - new_w) // 2
            y = avail.y() + (avail.height() - new_h) // 2
            self.setGeometry(x, y, new_w, new_h)
        elif new_screen:
            self._current_screen = new_screen

        # Re-show button bar after a short delay (let Qt finish DPI transition)
        if self._btn_bar:
            QTimer.singleShot(100, self._safe_reshow_btn_bar)
        # Re-show floating remove buttons
        if hasattr(self, '_cells'):
            QTimer.singleShot(150, self._show_floating_remove_btns)

    def _safe_reshow_btn_bar(self):
        """Safely reshow the button bar after drag/screen change."""
        if not self._btn_bar:
            return
        if not shiboken6.isValid(self):
            _log.warning("RESHOW BTN_BAR: self is invalid (C++ deleted)")
            return
        _log.debug("RESHOW BTN_BAR: reshowing")
        try:
            if self.isVisible() and not self.isMinimized():
                self._btn_bar.reposition()
                self._btn_bar.show()
                self._btn_bar.raise_()
        except RuntimeError:
            pass

    def _get_file_paths(self):
        """Return list of file paths this viewer is showing."""
        # GridView stores all files in _file_paths
        if hasattr(self, '_file_paths'):
            return [str(p) for p in self._file_paths]
        # Single viewers: return just the current file
        if hasattr(self, '_file_list') and self._file_list:
            idx = getattr(self, '_current_index', 0)
            if 0 <= idx < len(self._file_list):
                return [str(self._file_list[idx])]
            return [str(self._file_list[0])]
        return []

    def _do_merge(self, target):
        """Merge this window's files with target's files into a grid."""
        from PySide6.QtCore import QTimer

        _log.info(f"MERGE: starting merge, self={type(self).__name__}, target={type(target).__name__}")

        my_files = self._get_file_paths()
        target_files = target._get_file_paths()
        combined = target_files + my_files

        if not combined:
            _log.warning("MERGE: no files to combine")
            return

        # Remember target geometry for the new grid
        geo = target.geometry()

        _log.info(f"MERGE: closing windows, combined={len(combined)} files")

        # Close both windows first
        self.close()
        target.close()

        # Defer grid creation to let Qt finish processing close events
        def _create_merged_grid():
            from peek.grid_view import GridView
            from peek.config import config
            _log.info("MERGE: creating grid (deferred)")
            try:
                grid = GridView(combined, max_columns=config.get("grid_max_columns", 4))
                grid.setGeometry(geo)
                grid.show()
                _log.info("MERGE: grid shown successfully")
            except Exception as e:
                _log.error(f"MERGE CRASH: {e}", exc_info=True)

        QTimer.singleShot(50, _create_merged_grid)

    def _unregister_viewer(self):
        """Remove this window from the class-level registry."""
        if self in ResizeMixin._all_viewers:
            ResizeMixin._all_viewers.remove(self)

    def _do_resize(self, global_pos):
        delta = global_pos - self._resize_start_pos
        geo = QRect(self._resize_start_geo)
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()

        if self._resize_edge & _EDGE_LEFT:
            new_left = geo.left() + delta.x()
            if geo.right() - new_left >= min_w:
                geo.setLeft(new_left)
        if self._resize_edge & _EDGE_RIGHT:
            new_right = geo.right() + delta.x()
            if new_right - geo.left() >= min_w:
                geo.setRight(new_right)
        if self._resize_edge & _EDGE_TOP:
            new_top = geo.top() + delta.y()
            if geo.bottom() - new_top >= min_h:
                geo.setTop(new_top)
        if self._resize_edge & _EDGE_BOTTOM:
            new_bottom = geo.bottom() + delta.y()
            if new_bottom - geo.top() >= min_h:
                geo.setBottom(new_bottom)

        self.setGeometry(geo)
