from pathlib import Path

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QPainter, QDragEnterEvent, QDropEvent
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication, QMenu, QLabel

from peek.utils import get_media_files, is_video, is_media
from peek.resizable import ResizeMixin


class VideoPlayer(ResizeMixin, QWidget):
    closed = Signal()
    playback_finished = Signal()

    def __init__(self, file_path=None, file_list=None, loop=True, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setStyleSheet("background-color: black;")
        self.setMinimumSize(200, 200)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._video_widget = QVideoWidget(self)
        self._video_widget.setStyleSheet("background-color: black;")
        self._video_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._layout.addWidget(self._video_widget)

        self._error_label = QLabel(self)
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setStyleSheet("color: #ff4444; font-size: 14px; background: black;")
        self._error_label.hide()
        self._layout.addWidget(self._error_label)

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_widget)
        self._audio.setVolume(1.0)
        self._audio.setMuted(True)

        self._loop = loop
        self._paused = False
        self._is_fullscreen = False

        self._file_list = file_list or []
        self._current_index = 0

        self._resize_init()
        self.setAcceptDrops(True)

        self._player.mediaStatusChanged.connect(self._on_status_changed)
        self._player.errorOccurred.connect(self._on_error)

        if file_path:
            file_path = Path(file_path)
            if not self._file_list:
                self._file_list = [f for f in get_media_files(file_path.parent) if is_video(f)]
            try:
                self._current_index = [str(f) for f in self._file_list].index(str(file_path))
            except ValueError:
                self._current_index = 0
            self._play_file(file_path)

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

    def _play_file(self, file_path):
        file_path = Path(file_path)
        self._error_label.hide()
        self._video_widget.show()
        url = QUrl.fromLocalFile(str(file_path.resolve()))
        self._player.setSource(url)
        self._player.play()
        self._paused = False

    def load_file(self, file_path, file_list=None):
        file_path = Path(file_path)
        if file_list is not None:
            self._file_list = file_list
        if not self._file_list:
            self._file_list = [f for f in get_media_files(file_path.parent) if is_video(f)]
        try:
            self._current_index = [str(f) for f in self._file_list].index(str(file_path))
        except ValueError:
            self._current_index = 0
        self._play_file(file_path)

    def _navigate(self, delta):
        if not self._file_list:
            return
        self._current_index = (self._current_index + delta) % len(self._file_list)
        self._play_file(self._file_list[self._current_index])

    def current_file(self):
        if self._file_list and 0 <= self._current_index < len(self._file_list):
            return self._file_list[self._current_index]
        return None

    def stop(self):
        self._player.stop()

    def _on_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self._loop:
                self._player.setPosition(0)
                self._player.play()
            else:
                self.playback_finished.emit()

    def _on_error(self, error, error_string):
        self._video_widget.hide()
        self._error_label.setText(f"Playback error:\n{error_string}")
        self._error_label.show()

    # --- Events ---

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Space:
            self._toggle_pause()
        elif key == Qt.Key.Key_Right or key == Qt.Key.Key_D:
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
        elif key == Qt.Key.Key_Up:
            vol = min(self._audio.volume() + 0.1, 1.0)
            self._audio.setVolume(vol)
        elif key == Qt.Key.Key_Down:
            vol = max(self._audio.volume() - 0.1, 0.0)
            self._audio.setVolume(vol)
        elif key == Qt.Key.Key_M:
            self._audio.setMuted(not self._audio.isMuted())
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if self._resize_mouse_press(event):
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_pause()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        self._resize_mouse_move(event)

    def mouseReleaseEvent(self, event):
        self._resize_mouse_release(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_fullscreen()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            vol = min(self._audio.volume() + 0.05, 1.0)
        else:
            vol = max(self._audio.volume() - 0.05, 0.0)
        self._audio.setVolume(vol)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_fs_btn()
        self._raise_grab_handle()

    def closeEvent(self, event):
        self._unregister_viewer()
        self._player.stop()
        self.closed.emit()
        super().closeEvent(event)

    def _toggle_pause(self):
        if self._paused:
            self._player.play()
            self._paused = False
        else:
            self._player.pause()
            self._paused = True

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

        pause_action = menu.addAction("Resume" if self._paused else "Pause")
        pause_action.triggered.connect(self._toggle_pause)

        loop_action = menu.addAction("Loop: ON" if self._loop else "Loop: OFF")
        loop_action.triggered.connect(self._toggle_loop)

        menu.addSeparator()

        loc_action = menu.addAction("Open File Location")
        loc_action.triggered.connect(self._open_file_location)

        menu.addSeparator()

        info = menu.addAction(f"{len(self._file_list)} files  |  {self._current_index + 1}/{len(self._file_list)}")
        info.setEnabled(False)

        menu.exec(pos)

    def _toggle_loop(self):
        self._loop = not self._loop

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
        _log.info(f"VIDEO CONVERT_TO_GRID: {len(combined)} files")

        geo = self.geometry()
        self._player.stop()
        _log.info("VIDEO CONVERT_TO_GRID: hiding window")
        if hasattr(self, '_btn_bar') and self._btn_bar:
            self._btn_bar.hide()
        if hasattr(self, '_grab_handle') and self._grab_handle:
            self._grab_handle.hide()
        self.hide()
        _log.info("VIDEO CONVERT_TO_GRID: window hidden, scheduling delete")
        self.deleteLater()

        def _create_grid():
            from peek.grid_view import GridView
            _log.info("VIDEO CONVERT_TO_GRID: creating grid (deferred)")
            try:
                grid = GridView([str(f) for f in combined], max_columns=config.get("grid_max_columns", 4))
                grid.setGeometry(geo)
                grid.show()
                _log.info("VIDEO CONVERT_TO_GRID: grid shown")
            except Exception as e:
                _log.error(f"VIDEO CONVERT_TO_GRID CRASH: {e}", exc_info=True)

        QTimer.singleShot(50, _create_grid)
