from pathlib import Path
import random

from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget, QLabel, QApplication, QStackedLayout, QSizePolicy
from PIL import Image

from peek.utils import is_image, is_video, fit_size


class SlideshowView(QWidget):
    closed = Signal()

    def __init__(self, file_paths, interval=5, order="sequential", parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setStyleSheet("background-color: black;")

        self._file_paths = [Path(p) for p in file_paths]
        self._interval = interval
        self._order = order
        self._current_index = 0
        self._paused = False
        self._is_video_playing = False

        if self._order == "random":
            random.shuffle(self._file_paths)

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background: black;")
        self._image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._video_widget = QVideoWidget(self)
        self._video_widget.setStyleSheet("background: black;")

        self._stack.addWidget(self._image_label)
        self._stack.addWidget(self._video_widget)

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._audio.setVolume(1.0)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_widget)
        self._player.mediaStatusChanged.connect(self._on_video_status)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

        self._pixmap = None

        self.showFullScreen()

        if self._file_paths:
            self._show_current()

    def _show_current(self):
        if not self._file_paths:
            return

        self._timer.stop()
        self._player.stop()
        self._is_video_playing = False

        fp = self._file_paths[self._current_index]

        if is_image(fp):
            self._show_image(fp)
            self._stack.setCurrentWidget(self._image_label)
            if not self._paused:
                self._timer.start(self._interval * 1000)
        elif is_video(fp):
            self._play_video(fp)
            self._stack.setCurrentWidget(self._video_widget)
            self._is_video_playing = True

    def _show_image(self, file_path):
        try:
            pil_img = Image.open(file_path)
            pil_img = pil_img.convert("RGBA")
            data = pil_img.tobytes("raw", "RGBA")
            qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
            self._pixmap = QPixmap.fromImage(qimg.copy())
            self._render_image()
        except Exception:
            self._image_label.setText("Error")

    def _render_image(self):
        if not self._pixmap:
            return
        w, h = self.width(), self.height()
        fw, fh = fit_size(self._pixmap.width(), self._pixmap.height(), w, h)
        scaled = self._pixmap.scaled(fw, fh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        canvas = QPixmap(w, h)
        canvas.fill(Qt.GlobalColor.black)
        painter = QPainter(canvas)
        x = (w - scaled.width()) // 2
        y = (h - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()
        self._image_label.setPixmap(canvas)

    def _play_video(self, file_path):
        url = QUrl.fromLocalFile(str(Path(file_path).resolve()))
        self._player.setSource(url)
        self._player.play()

    def _on_video_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._is_video_playing = False
            if not self._paused:
                self._advance()

    def _advance(self):
        self._timer.stop()
        self._current_index = (self._current_index + 1) % len(self._file_paths)
        self._show_current()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
        elif key == Qt.Key.Key_Space:
            self._toggle_pause()
        elif key == Qt.Key.Key_Right or key == Qt.Key.Key_D:
            self._advance()
        elif key == Qt.Key.Key_Left or key == Qt.Key.Key_A:
            self._current_index = (self._current_index - 2) % len(self._file_paths)
            self._advance()
        elif key == Qt.Key.Key_Up:
            vol = min(self._audio.volume() + 0.1, 1.0)
            self._audio.setVolume(vol)
        elif key == Qt.Key.Key_Down:
            vol = max(self._audio.volume() - 0.1, 0.0)
            self._audio.setVolume(vol)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_pause()

    def mouseDoubleClickEvent(self, event):
        self.close()

    def _toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            self._timer.stop()
            if self._is_video_playing:
                self._player.pause()
        else:
            if self._is_video_playing:
                self._player.play()
            elif is_image(self._file_paths[self._current_index]):
                self._timer.start(self._interval * 1000)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap and not self._is_video_playing:
            self._render_image()

    def closeEvent(self, event):
        self._timer.stop()
        self._player.stop()
        self.closed.emit()
        super().closeEvent(event)
