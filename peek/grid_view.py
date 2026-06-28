import math
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QUrl, QMimeData, QPoint, QTimer
from PySide6.QtGui import QPixmap, QImage, QPainter, QDragEnterEvent, QDropEvent, QMovie
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QWidget, QLabel, QApplication, QSizePolicy, QFrame, QPushButton,
)
from PIL import Image

from peek.utils import is_image, is_video, fit_size
from peek.resizable import ResizeMixin
import logging
_log = logging.getLogger("rfab_viewer")

_GAP = 2
_DRAG_THRESHOLD = 12

_REMOVE_BTN_STYLE = (
    "QPushButton { background: rgba(255,255,255,0.06); "
    "color: rgba(255,255,255,0.25); "
    "border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; "
    "font-size: 14px; padding: 0; }"
    "QPushButton:hover { background: rgba(255,255,255,0.15); "
    "color: rgba(255,255,255,0.7); "
    "border-color: rgba(255,255,255,0.25); }"
)


def _get_aspect(fp):
    """Get width/height aspect ratio of a file."""
    if is_image(fp):
        try:
            img = Image.open(fp)
            w, h = img.size
            img.close()
            return w / max(h, 1)
        except Exception:
            return 1.0
    return 16 / 9


def _compute_rows(aspects, max_cols):
    """Partition images into rows of at most max_cols each."""
    rows = []
    i = 0
    n = len(aspects)
    while i < n:
        rows.append(list(range(i, min(i + max_cols, n))))
        i += max_cols
    return rows




class GridCell(QFrame):
    remove_requested = Signal(int)

    def __init__(self, index, file_path, aspect, parent=None):
        super().__init__(parent)
        self.index = index
        self.file_path = Path(file_path)
        self.aspect = aspect
        self.setStyleSheet("background-color: black;")
        self.setMouseTracking(True)

        self._player = None
        self._audio = None

        _log.debug(f"CELL {index}: setting up media for {file_path}")
        if is_image(file_path):
            _log.debug(f"CELL {index}: calling _setup_image")
            self._setup_image()
        elif is_video(file_path):
            _log.debug(f"CELL {index}: calling _setup_video")
            self._setup_video()

        # Always-visible remove button (top-center)
        if is_video(file_path):
            # Video uses native surface — button must float above it
            self._remove_btn = QPushButton("\u2715")
            self._remove_btn.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowStaysOnTopHint
            )
            self._remove_btn.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            self._remove_btn.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._remove_btn_floating = True
        else:
            self._remove_btn = QPushButton("\u2715", self)
            self._remove_btn_floating = False
        self._remove_btn.setFixedSize(28, 28)
        self._remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_btn.setStyleSheet(_REMOVE_BTN_STYLE)
        self._remove_btn.clicked.connect(self._on_remove)
        _log.debug(f"CELL {index}: created, floating={getattr(self, '_remove_btn_floating', False)}")

    def _on_remove(self):
        _log.info(f"CELL {self.index}: remove requested")
        self.remove_requested.emit(self.index)

    def _setup_image(self):
        _log.debug(f"CELL: _setup_image start for {self.file_path}")
        label = QLabel(self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("border: none;")
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._label = label
        self._movie = None

        # Animated GIF support
        if self.file_path.suffix.lower() == '.gif':
            _log.info(f"CELL GIF: detected .gif, trying QMovie for {self.file_path}")
            try:
                movie = QMovie(str(self.file_path))
                _log.info(f"CELL GIF: isValid={movie.isValid()} frameCount={movie.frameCount()}")
                if movie.isValid():
                    self._movie = movie
                    self._movie.setCacheMode(QMovie.CacheMode.CacheAll)
                    label.setMovie(self._movie)
                    self._movie.start()
                    self._pixmap = None
                    _log.info(f"CELL GIF: movie started, state={self._movie.state()}")
                    return
            except Exception as e:
                _log.error(f"CELL GIF: exception {e}")

        try:
            pil_img = Image.open(self.file_path)
            pil_img = pil_img.convert("RGBA")
            data = pil_img.tobytes("raw", "RGBA")
            qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
            self._pixmap = QPixmap.fromImage(qimg.copy())
        except Exception:
            self._pixmap = None
            label.setText("Error")
            label.setStyleSheet("color: #ff4444; border: none;")

    def _setup_video(self):
        _log.debug(f"CELL: _setup_video start for {self.file_path}")
        self._video_widget = QVideoWidget(self)
        self._video_widget.setStyleSheet("border: none;")
        self._video_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._audio.setVolume(0.0)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_widget)
        self._player.mediaStatusChanged.connect(self._on_status)

        url = QUrl.fromLocalFile(str(self.file_path.resolve()))
        self._player.setSource(url)
        self._player.play()

    def _on_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._player.setPosition(0)
            self._player.play()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()

        if hasattr(self, "_label"):
            self._label.setGeometry(0, 0, w, h)
            if getattr(self, '_movie', None):
                from PySide6.QtCore import QSize
                self._movie.setScaledSize(QSize(w, h))
            elif self._pixmap:
                # Skip scaling entirely during active resize for smooth drag
                parent = self.parentWidget()
                if getattr(parent, '_resize_active', False):
                    return
                fw, fh = fit_size(self._pixmap.width(), self._pixmap.height(), w, h)
                scaled = self._pixmap.scaled(fw, fh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self._label.setPixmap(scaled)

        if hasattr(self, "_video_widget"):
            self._video_widget.setGeometry(0, 0, w, h)

        # Position remove button top-right
        if hasattr(self, "_remove_btn"):
            self._remove_btn.move((w - 28) // 2, 4)
            self._remove_btn.raise_()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            parent = self.parentWidget()
            if parent and hasattr(parent, '_resize_mouse_press'):
                from peek.resizable import _detect_edge, _EDGE_NONE
                parent_pos = self.mapTo(parent, event.position().toPoint())
                edge = _detect_edge(parent, parent_pos)
                if edge != _EDGE_NONE or parent_pos.y() <= getattr(parent, '_DRAG_ZONE_HEIGHT', 50):
                    event.ignore()
                    return
            # Record for drag reorder (GridView reads this)
            if parent and hasattr(parent, '_start_cell_drag'):
                parent._start_cell_drag(self, event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        parent = self.parentWidget()
        if parent and hasattr(parent, '_continue_cell_drag'):
            parent._continue_cell_drag(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            parent = self.parentWidget()
            if parent and hasattr(parent, '_end_cell_drag'):
                parent._end_cell_drag()

    def mouseDoubleClickEvent(self, event):
        event.accept()

    def cleanup(self):
        if getattr(self, '_remove_btn_floating', False) and hasattr(self, '_remove_btn'):
            self._remove_btn.close()
        if self._player:
            self._player.stop()
        if getattr(self, '_movie', None):
            self._movie.stop()


class GridView(ResizeMixin, QWidget):
    cell_clicked = Signal(int, str)
    closed = Signal()

    def __init__(self, file_paths, max_columns=4, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setStyleSheet("background-color: #0a0a0a;")
        self.setMinimumSize(400, 300)

        self.file_paths = [Path(p) for p in file_paths]
        self._cells = []
        _log.debug(f"GRID: creating {len(file_paths)} cells")
        self._is_fullscreen = False
        self._max_columns = max_columns

        # Drag reorder state
        self._drag_cell = None
        # Debounce timer for layout during resize (video robustness)
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.setInterval(80)
        self._layout_timer.timeout.connect(self._do_layout)
        self._drag_start_pos = None
        self._dragging = False

        self._resize_active = False
        self._layout_mode = 'auto'  # 'auto', '1row', '2row'
        self._resize_init()
        self.setAcceptDrops(True)

        # Read aspect ratios and create cells
        self._aspects = [_get_aspect(fp) for fp in self.file_paths]
        for i, fp in enumerate(self.file_paths):
            cell = GridCell(i, fp, self._aspects[i], self)
            cell.remove_requested.connect(self._remove_cell)
            self._cells.append(cell)

        # Choose initial window size to fit content with no wasted space
        screen = QApplication.primaryScreen().availableGeometry()
        max_w = int(screen.width() * 0.92)
        max_h = int(screen.height() * 0.92)

        rows = _compute_rows(self._aspects, max_columns)
        # h_ratio = total_height / content_width for justified layout
        total_h_ratio = 0.0
        for row_indices in rows:
            row_aspect_sum = sum(self._aspects[i] for i in row_indices)
            total_h_ratio += 1.0 / max(row_aspect_sum, 0.1)
        # Add gap contribution
        gap_h = _GAP * (len(rows) + 1)

        # Try fitting to width first
        win_w = max_w
        win_h = int(win_w * total_h_ratio + gap_h)
        if win_h > max_h:
            # Too tall, fit to height instead
            win_h = max_h
            win_w = int((win_h - gap_h) / max(total_h_ratio, 0.01))
        win_w = max(400, min(win_w, max_w))
        win_h = max(300, min(win_h, max_h))

        self.resize(win_w, win_h)
        self._center_on_screen()
        self._create_fullscreen_btn()
        self._add_layout_buttons()
        self._do_layout()
        # Hide remove button when only one cell (window X suffices)
        if len(self._cells) == 1:
            self._cells[0]._remove_btn.hide()

    def _do_layout(self):
        """Position cells using justified row layout -- images fill space perfectly."""
        _log.debug(f"_do_layout: w={self.width()} h={self.height()} cells={len(self._cells)}")
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0 or not self._cells:
            return

        content_w = w - _GAP * 2
        if content_w <= 0:
            return

        n = len(self._aspects)
        use_cols = 1
        use_score = float('inf')
        for tc in range(1, min(n, self._max_columns) + 1):
            tr = _compute_rows(self._aspects, tc)
            tg = _GAP * (len(tr) + 1)
            nh = tg
            for ri in tr:
                nh += content_w / max(sum(self._aspects[k] for k in ri), 0.1)
            sc = h / max(nh, 1)
            s = abs(math.log(max(sc, 0.01)))
            if s < use_score:
                use_score = s
                use_cols = tc

        rows = _compute_rows(self._aspects, use_cols)

        row_natural_heights = []
        for row_indices in rows:
            row_aspect_sum = sum(self._aspects[i] for i in row_indices)
            row_natural_heights.append(content_w / max(row_aspect_sum, 0.1))

        total_gaps = _GAP * (len(rows) + 1)
        available_h = h - total_gaps
        natural_sum = sum(row_natural_heights)
        scale = available_h / max(natural_sum, 1)

        y = _GAP
        for row_idx, row_indices in enumerate(rows):
            row_h = max(1, int(row_natural_heights[row_idx] * scale))
            row_aspect_sum = sum(self._aspects[i] for i in row_indices)
            x = _GAP
            for j, cell_idx in enumerate(row_indices):
                frac = self._aspects[cell_idx] / max(row_aspect_sum, 0.1)
                cell_w = int(frac * content_w)
                # Last cell in row gets remaining width (avoid rounding gaps)
                if j == len(row_indices) - 1:
                    cell_w = w - _GAP - x
                self._cells[cell_idx].setGeometry(x, y, max(cell_w, 1), row_h)
                self._cells[cell_idx].show()
                x += cell_w + _GAP
            y += row_h + _GAP
        self._raise_grab_handle()
        _log.debug(f"GRID INIT: {len(self._cells)} cells created")
        # Delay floating button show to after window is on screen
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._show_floating_remove_btns)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.x()
        y = (screen.height() - self.height()) // 2 + screen.y()
        self.move(x, y)

    def _on_cell_clicked(self, index):
        if 0 <= index < len(self.file_paths):
            self.cell_clicked.emit(index, str(self.file_paths[index]))

    def _remove_cell(self, index):
        """Remove a file from the grid by cell index."""
        if index < 0 or index >= len(self._cells):
            return
        if len(self._cells) <= 1:
            self.close()
            return
        cell = self._cells[index]
        cell.cleanup()
        cell.hide()
        cell.deleteLater()
        del self._cells[index]
        del self.file_paths[index]
        del self._aspects[index]
        for i, c in enumerate(self._cells):
            c.index = i
        # Hide remove button when only one cell remains (window X suffices)
        if len(self._cells) == 1:
            self._cells[0]._remove_btn.hide()
        self._do_layout()

    # -- Drag reorder (called by GridCell mouse handlers) --
    def _start_cell_drag(self, cell, global_pos):
        self._drag_cell = cell
        self._drag_start_pos = global_pos
        self._dragging = False

    def _continue_cell_drag(self, global_pos):
        if not self._drag_cell or not self._drag_start_pos:
            return
        dist = (global_pos - self._drag_start_pos).manhattanLength()
        if dist >= _DRAG_THRESHOLD:
            self._dragging = True
            pos = self.mapFromGlobal(global_pos)
            self._update_drag_reorder(pos)

    def _end_cell_drag(self):
        self._drag_cell = None
        self._drag_start_pos = None
        self._dragging = False

    def _update_drag_reorder(self, pos):
        """During drag, swap the dragged cell with whatever cell is under the cursor."""
        if not self._drag_cell or self._drag_cell not in self._cells:
            return
        src = self._drag_cell.index
        for cell in self._cells:
            if cell is not self._drag_cell and cell.geometry().contains(pos):
                dst = cell.index
                # Swap in all parallel lists
                self._cells[src], self._cells[dst] = self._cells[dst], self._cells[src]
                self.file_paths[src], self.file_paths[dst] = self.file_paths[dst], self.file_paths[src]
                self._aspects[src], self._aspects[dst] = self._aspects[dst], self._aspects[src]
                self._cells[src].index = src
                self._cells[dst].index = dst
                self._do_layout()
                break

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_fs_btn()
        # Debounce layout during resize for video robustness
        self._layout_timer.start()

    def _show_floating_remove_btns(self):
        """Position and show floating remove buttons for video cells."""
        if not self.isVisible() or len(self._cells) <= 1:
            return
        _log.debug(f"FLOAT BTNS: showing for {len(self._cells)} cells")
        for c in self._cells:
            if getattr(c, "_remove_btn_floating", False):
                try:
                    w = c.width()
                    gp = c.mapToGlobal(c.rect().topLeft())
                    c._remove_btn.move(gp.x() + (w - 28) // 2, gp.y() + 4)
                    if c._remove_btn.isHidden():
                        c._remove_btn.show()
                except RuntimeError:
                    pass

    def moveEvent(self, event):
        super().moveEvent(event)
        _log.debug(f"GRID MOVE: pos={self.pos().x()},{self.pos().y()}")
        # Reposition floating remove buttons on video cells
        for cell in self._cells:
            if getattr(cell, '_remove_btn_floating', False) and hasattr(cell, '_remove_btn'):
                w = cell.width()
                gp = cell.mapToGlobal(cell.rect().topLeft())
                cell._remove_btn.move(gp.x() + (w - 28) // 2, gp.y() + 4)

    def hideEvent(self, event):
        super().hideEvent(event)
        for cell in self._cells:
            if getattr(cell, '_remove_btn_floating', False) and hasattr(cell, '_remove_btn'):
                cell._remove_btn.hide()

    def showEvent(self, event):
        super().showEvent(event)
        if len(self._cells) > 1:
            for cell in self._cells:
                if getattr(cell, '_remove_btn_floating', False) and hasattr(cell, '_remove_btn'):
                    cell._remove_btn.show()
        if self._btn_bar:
            QTimer.singleShot(200, self._safe_reshow_btn_bar)

    def mousePressEvent(self, event):
        if self._resize_mouse_press(event):
            self._resize_active = True
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_resizing = self._resize_active
        self._resize_active = False
        self._resize_mouse_release(event)
        if was_resizing:
            self._finalize_resize()

    def _finalize_resize(self):
        """Force one final smooth-quality render after resize completes."""
        for cell in self._cells:
            if hasattr(cell, '_label') and hasattr(cell, '_pixmap') and cell._pixmap:
                w, h = cell.width(), cell.height()
                fw, fh = fit_size(cell._pixmap.width(), cell._pixmap.height(), w, h)
                scaled = cell._pixmap.scaled(fw, fh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                cell._label.setPixmap(scaled)

    def keyPressEvent(self, event):
        key = event.key()
        _log.info(f"GRID KEY: {key}")
        if key == Qt.Key.Key_Escape:
            if self._is_fullscreen:
                self._toggle_fullscreen()
            else:
                self.close()
        elif key == Qt.Key.Key_F:
            self._toggle_fullscreen()
        elif key == Qt.Key.Key_Left:
            self._max_columns = max(1, self._max_columns - 1)
            _log.info(f"GRID KEY LEFT: max_columns now {self._max_columns}")
            self._do_layout()
        elif key == Qt.Key.Key_Right:
            self._max_columns = min(len(self._cells), self._max_columns + 1)
            _log.info(f"GRID KEY RIGHT: max_columns now {self._max_columns}")
            self._do_layout()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Absorb double-clicks — do nothing (prevent default which re-fires mousePressEvent)
        event.accept()

    def _toggle_fullscreen(self):
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._is_fullscreen = True

    def _add_layout_buttons(self):
        """Add layout mode buttons (auto grid / 1 row / 2 rows) to the button bar."""
        from peek.resizable import _WC_BTN_STYLE
        if not self._btn_bar:
            return

        auto_btn = QPushButton("\u25a6", self._btn_bar)
        auto_btn.setFixedSize(28, 28)
        auto_btn.setStyleSheet(_WC_BTN_STYLE)
        auto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        auto_btn.setToolTip("Auto grid layout")
        auto_btn.clicked.connect(self._set_layout_auto)
        self._wc_buttons.insert(0, auto_btn)

        row1_btn = QPushButton("\u25ac", self._btn_bar)
        row1_btn.setFixedSize(28, 28)
        row1_btn.setStyleSheet(_WC_BTN_STYLE)
        row1_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1_btn.setToolTip("Single row layout")
        row1_btn.clicked.connect(self._set_layout_1row)
        self._wc_buttons.insert(1, row1_btn)

        row2_btn = QPushButton("\u2261", self._btn_bar)
        row2_btn.setFixedSize(28, 28)
        row2_btn.setStyleSheet(_WC_BTN_STYLE)
        row2_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row2_btn.setToolTip("Two row layout")
        row2_btn.clicked.connect(self._set_layout_2row)
        self._wc_buttons.insert(2, row2_btn)

        self._btn_bar.reposition()

    def _set_layout_auto(self):
        self._layout_mode = 'auto'
        self._max_columns = 4
        self._do_layout()

    def _set_layout_1row(self):
        self._layout_mode = '1row'
        self._max_columns = len(self._cells)
        self._do_layout()

    def _set_layout_2row(self):
        self._layout_mode = '2row'
        import math
        self._max_columns = max(1, math.ceil(len(self._cells) / 2))
        self._do_layout()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        new_files = []
        for url in urls:
            p = Path(url.toLocalFile())
            if p.is_file() and (is_image(p) or is_video(p)):
                new_files.append(p)
        if new_files:
            self._add_files(new_files)

    def _add_files(self, new_files):
        """Add new files to the grid dynamically."""
        for fp in new_files:
            if fp not in self.file_paths:
                self.file_paths.append(fp)
                a = _get_aspect(fp)
                self._aspects.append(a)
                idx = len(self._cells)
                cell = GridCell(idx, fp, a, self)
                cell.remove_requested.connect(self._remove_cell)
                self._cells.append(cell)
        self._do_layout()

    def closeEvent(self, event):
        self._unregister_viewer()
        for cell in self._cells:
            cell.cleanup()
        self.closed.emit()
        super().closeEvent(event)
