from pathlib import Path

from PySide6.QtCore import Qt, QPoint, Signal, QUrl, QByteArray
from PySide6.QtGui import QPixmap, QImage, QPainter, QCursor, QAction, QKeySequence, QDragEnterEvent, QDropEvent, QMovie
from PySide6.QtWidgets import (
    QWidget, QLabel, QApplication, QMenu, QSizePolicy,
)
from PIL import Image

from peek.utils import get_media_files, is_image, is_video, is_media, fit_size
from peek.resizable import ResizeMixin


class ImageViewer(ResizeMixin, QWidget):
    closed = Signal()
    request_next = Signal()
    request_prev = Signal()
    request_slideshow = Signal()
    request_grid = Signal()

    def __init__(self, file_path=None, file_list=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setStyleSheet("background-color: black;")
        self.setMinimumSize(200, 200)
        self.setAcceptDrops(True)

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._pixmap = None
        self._movie = None
        self._zoom = 1.0
        self._pan_offset = QPoint(0, 0)
        self._drag_start = None
        self._drag_start_offset = None
        self._is_fullscreen = False

        self._file_list = file_list or []
        self._current_index = 0

        self._resize_init()

        if file_path:
            file_path = Path(file_path)
            if not self._file_list:
                self._file_list = [f for f in get_media_files(file_path.parent) if is_image(f)]
            try:
                self._current_index = [str(f) for f in self._file_list].index(str(file_path))
            except ValueError:
                self._current_index = 0
            self._load_image(file_path)

        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.7), int(screen.height() * 0.7))
        self._center_on_screen()
        self._create_fullscreen_btn()
        # Delayed button bar show to handle focus timing on Windows
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._safe_reshow_btn_bar)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.x()
        y = (screen.height() - self.height()) // 2 + screen.y()
        self.move(x, y)

    def _stop_movie(self):
        if self._movie:
            self._movie.stop()
            self._label.setMovie(None)
            self._movie.deleteLater()
            self._movie = None

    def _load_image(self, file_path):
        file_path = Path(file_path)
        self._stop_movie()
        # Animated GIF support
        if file_path.suffix.lower() == '.gif':
            try:
                movie = QMovie(str(file_path))
                if movie.isValid():
                    # frameCount() may return 0 before caching; treat all valid GIFs as animated
                    self._pixmap = None
                    self._movie = movie
                    self._movie.setCacheMode(QMovie.CacheMode.CacheAll)
                    w, h = self.width(), self.height()
                    if w > 0 and h > 0:
                        from PySide6.QtCore import QSize
                        self._movie.setScaledSize(QSize(w, h))
                    self._label.setGeometry(0, 0, max(w, 1), max(h, 1))
                    self._label.setMovie(self._movie)
                    self._movie.start()
                    self._zoom = 1.0
                    self._pan_offset = QPoint(0, 0)
                    return
            except Exception:
                pass
        try:
            pil_img = Image.open(file_path)
            pil_img = pil_img.convert("RGBA")
            data = pil_img.tobytes("raw", "RGBA")
            qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
            self._pixmap = QPixmap.fromImage(qimg.copy())
            self._zoom = 1.0
            self._pan_offset = QPoint(0, 0)
            self._render()
        except Exception as e:
            self._label.setText(f"Error loading image:\n{e}")
            self._label.setStyleSheet("color: #ff4444; font-size: 14px;")

    def _render(self, force_smooth=False):
        if not self._pixmap:
            return
        w, h = self.width(), self.height()
        fw, fh = fit_size(self._pixmap.width(), self._pixmap.height(), w, h)
        fw = int(fw * self._zoom)
        fh = int(fh * self._zoom)
        # Use fast scaling during active resize for smooth UX
        if not force_smooth and getattr(self, '_resize_active', False):
            mode = Qt.TransformationMode.FastTransformation
        else:
            mode = Qt.TransformationMode.SmoothTransformation
        scaled = self._pixmap.scaled(fw, fh, Qt.AspectRatioMode.KeepAspectRatio, mode)

        canvas = QPixmap(w, h)
        canvas.fill(Qt.GlobalColor.black)
        painter = QPainter(canvas)
        x = (w - scaled.width()) // 2 + self._pan_offset.x()
        y = (h - scaled.height()) // 2 + self._pan_offset.y()
        painter.drawPixmap(x, y, scaled)
        painter.end()

        self._label.setGeometry(0, 0, w, h)
        self._label.setPixmap(canvas)

    def load_file(self, file_path, file_list=None):
        file_path = Path(file_path)
        if file_list is not None:
            self._file_list = file_list
        if not self._file_list:
            self._file_list = [f for f in get_media_files(file_path.parent) if is_image(f)]
        try:
            self._current_index = [str(f) for f in self._file_list].index(str(file_path))
        except ValueError:
            self._current_index = 0
        self._load_image(file_path)

    def _navigate(self, delta):
        if not self._file_list:
            return
        self._current_index = (self._current_index + delta) % len(self._file_list)
        self._load_image(self._file_list[self._current_index])

    def current_file(self):
        if self._file_list and 0 <= self._current_index < len(self._file_list):
            return self._file_list[self._current_index]
        return None

    # --- Events ---

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_fs_btn()
        self._raise_grab_handle()
        w, h = self.width(), self.height()
        self._label.setGeometry(0, 0, w, h)
        # Skip expensive rendering during active resize
        if getattr(self, '_resize_active', False):
            return
        if self._movie:
            from PySide6.QtCore import QSize
            self._movie.setScaledSize(QSize(w, h))
        else:
            self._render()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Right or key == Qt.Key.Key_D:
            self._navigate(1)
        elif key == Qt.Key.Key_Left or key == Qt.Key.Key_A:
            self._navigate(-1)
        elif key == Qt.Key.Key_Escape:
            if self._is_fullscreen:
                self._toggle_fullscreen()
            else:
                self.close()
        elif key == Qt.Key.Key_F:
            self._toggle_fullscreen()
        elif key == Qt.Key.Key_R:
            self._zoom = 1.0
            self._pan_offset = QPoint(0, 0)
            self._render()
        elif key == Qt.Key.Key_S:
            self.request_slideshow.emit()
        elif key == Qt.Key.Key_G:
            self.request_grid.emit()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom = min(self._zoom * 1.15, 20.0)
        else:
            self._zoom = max(self._zoom / 1.15, 0.1)
        self._render()

    def mousePressEvent(self, event):
        if self._resize_mouse_press(event):
            self._resize_active = True
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._drag_start_offset = QPoint(self._pan_offset)
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._resize_mouse_move(event):
            return
        if self._drag_start is not None:
            delta = event.globalPosition().toPoint() - self._drag_start
            self._pan_offset = self._drag_start_offset + delta
            self._render()

    def mouseReleaseEvent(self, event):
        was_resizing = getattr(self, '_resize_active', False)
        self._resize_active = False
        if self._resize_mouse_release(event):
            if was_resizing:
                self._render(force_smooth=True)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_fullscreen()

    def closeEvent(self, event):
        self._stop_movie()
        self._unregister_viewer()
        self.closed.emit()
        super().closeEvent(event)

    def _toggle_fullscreen(self):
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._is_fullscreen = True

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #1a1a2e; color: #e0e0e0; border: 1px solid #333; padding: 4px; }
            QMenu::item:selected { background: #16213e; }
        """)

        copy_action = menu.addAction("Copy Image")
        copy_action.triggered.connect(self._copy_to_clipboard)

        loc_action = menu.addAction("Open File Location")
        loc_action.triggered.connect(self._open_file_location)

        menu.addSeparator()

        info = menu.addAction(f"{len(self._file_list)} files  |  {self._current_index + 1}/{len(self._file_list)}")
        info.setEnabled(False)

        menu.exec(pos)

    def _copy_to_clipboard(self):
        if self._pixmap:
            QApplication.clipboard().setPixmap(self._pixmap)

    def _open_file_location(self):
        import subprocess, sys
        current = self.current_file()
        if not current:
            return
        current = Path(current)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(current)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(current)])
        else:
            subprocess.Popen(["xdg-open", str(current.parent)])

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        new_files = []
        for url in urls:
            p = Path(url.toLocalFile())
            if p.is_file() and is_media(p):
                new_files.append(p)
        if new_files:
            self._convert_to_grid(new_files)

    def _convert_to_grid(self, new_files):
        """Convert this viewer to a grid with current file + dropped files."""
        from peek.config import config
        from PySide6.QtCore import QTimer
        import logging
        _log = logging.getLogger('rfab_viewer')

        current = self.current_file()
        combined = []
        if current:
            combined.append(Path(current))
        combined.extend(new_files)
        _log.info(f"CONVERT_TO_GRID: {len(combined)} files")

        geo = self.geometry()
        _log.info("CONVERT_TO_GRID: hiding window")
        # Hide + deleteLater instead of close() to avoid native crash
        if hasattr(self, '_btn_bar') and self._btn_bar:
            self._btn_bar.hide()
        if hasattr(self, '_grab_handle') and self._grab_handle:
            self._grab_handle.hide()
        self.hide()
        _log.info("CONVERT_TO_GRID: window hidden, scheduling delete")
        self.deleteLater()

        # Defer grid creation to let Qt finish close cleanup
        def _create_grid():
            from peek.grid_view import GridView
            _log.info("CONVERT_TO_GRID: creating grid (deferred)")
            try:
                grid = GridView([str(f) for f in combined], max_columns=config.get("grid_max_columns", 4))
                grid.setGeometry(geo)
                grid.show()
                _log.info("CONVERT_TO_GRID: grid shown")
            except Exception as e:
                _log.error(f"CONVERT_TO_GRID CRASH: {e}", exc_info=True)

        QTimer.singleShot(50, _create_grid)
