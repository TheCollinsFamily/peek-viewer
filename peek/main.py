import sys
from pathlib import Path

from PySide6.QtCore import Qt, QMimeData, QSize, QTimer, Signal, QObject
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QKeySequence, QShortcut, QIcon, QFont, QColor, QPalette,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog,
    QSpinBox, QComboBox, QCheckBox, QGroupBox, QMessageBox,
    QSystemTrayIcon, QMenu, QSizePolicy, QProgressBar, QTabWidget,
)

from peek.config import config
from peek.utils import (
    get_media_files, get_archive_files, is_image, is_video, is_media, is_archive,
    IMAGE_EXTENSIONS, VIDEO_EXTENSIONS,
)
from peek.image_viewer import ImageViewer
from peek.video_player import VideoPlayer
from peek.grid_view import GridView
from peek.slideshow import SlideshowView
from peek.unzipper import unzip_folder
from peek.boss_key import BossKey


DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: "Segoe UI", "SF Pro Display", sans-serif;
}
QPushButton {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #1f2937;
    border-color: #58a6ff;
}
QPushButton:pressed {
    background-color: #0d419d;
}
QPushButton#accent {
    background-color: #1f6feb;
    border-color: #1f6feb;
    color: white;
}
QPushButton#accent:hover {
    background-color: #388bfd;
}
QPushButton#danger {
    background-color: #b62324;
    border-color: #f85149;
}
QPushButton#danger:hover {
    background-color: #da3633;
}
QLabel {
    color: #c9d1d9;
}
QLabel#title {
    font-size: 22px;
    font-weight: bold;
    color: #f0f6fc;
}
QLabel#subtitle {
    font-size: 12px;
    color: #8b949e;
}
QLabel#dropzone {
    border: 2px dashed #30363d;
    border-radius: 12px;
    color: #8b949e;
    font-size: 15px;
    padding: 40px;
    background-color: #0d1117;
}
QLabel#dropzone:hover {
    border-color: #58a6ff;
    color: #58a6ff;
}
QListWidget {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px;
    font-size: 12px;
}
QListWidget::item {
    padding: 4px 8px;
    border-radius: 4px;
}
QListWidget::item:hover {
    background-color: #1f2937;
}
QListWidget::item:selected {
    background-color: #1f6feb;
}
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 20px;
    font-size: 13px;
    color: #8b949e;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QSpinBox, QComboBox {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px 8px;
}
QCheckBox {
    color: #c9d1d9;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #30363d;
    background: #161b22;
}
QCheckBox::indicator:checked {
    background: #1f6feb;
    border-color: #1f6feb;
}
QProgressBar {
    border: 1px solid #30363d;
    border-radius: 4px;
    background: #161b22;
    text-align: center;
    color: #c9d1d9;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #1f6feb;
    border-radius: 3px;
}
QMenu {
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    padding: 4px;
}
QMenu::item:selected {
    background: #1f2937;
}
QTabWidget::pane {
    border: 1px solid #30363d;
    border-top: none;
    background: #0d1117;
}
QTabBar::tab {
    background: #161b22;
    color: #8b949e;
    border: 1px solid #30363d;
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 13px;
}
QTabBar::tab:selected {
    background: #0d1117;
    color: #f0f6fc;
    border-bottom: 2px solid #58a6ff;
}
QTabBar::tab:hover:!selected {
    background: #1f2937;
    color: #c9d1d9;
}
"""


class DropZone(QLabel):
    files_dropped = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropzone")
        self.setText("Drop files or folders here\n\nImages · Videos · ZIP archives")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.styleSheet() + "border-color: #58a6ff; color: #58a6ff; background-color: #0d1f3c;")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        self.setObjectName("dropzone")

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        self.setObjectName("dropzone")
        urls = event.mimeData().urls()
        paths = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        if paths and self.files_dropped:
            self.files_dropped(paths)


class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RFab Viewer")
        self.setMinimumSize(480, 520)
        self.resize(520, 580)

        # Window icon
        icon_path = Path(__file__).resolve().parent.parent / "peek.ico"
        if not icon_path.exists() and hasattr(sys, '_MEIPASS'):
            icon_path = Path(sys._MEIPASS) / "peek.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._viewers = []
        self._boss_key = BossKey(self)
        self._boss_key.register_window(self)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(10)

        # --- Header ---
        header = QHBoxLayout()
        title = QLabel("RFab Viewer")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        subtitle = QLabel("rfab.ai")
        subtitle.setObjectName("subtitle")
        header.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(header)

        # --- Tabs ---
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs, stretch=1)

        self._tabs.addTab(self._build_open_tab(), "Open")
        self._tabs.addTab(self._build_slideshow_tab(), "Slideshow")
        self._tabs.addTab(self._build_tools_tab(), "Tools")

        # --- Boss key shortcut ---
        boss_shortcut = QShortcut(QKeySequence("Ctrl+`"), self)
        boss_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        boss_shortcut.activated.connect(self._boss_key.toggle)

        # --- System tray ---
        self._setup_tray()

        self._center_on_screen()

    # --- Tab builders ---

    def _build_open_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self._drop_zone = DropZone()
        self._drop_zone.files_dropped = self._handle_dropped
        layout.addWidget(self._drop_zone, stretch=1)

        browse_btn = QPushButton("Browse Files")
        browse_btn.setObjectName("accent")
        browse_btn.clicked.connect(self._open_grid)
        layout.addWidget(browse_btn)

        # Usage hint
        help_text = QLabel(
            "Select multiple files to view them side by side in a grid. "
            "Click any panel to open it full size. Videos auto-loop."
        )
        help_text.setObjectName("subtitle")
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(help_text)

        # One-click default viewer setup
        register_btn = QPushButton("Set RFab Viewer as Default")
        register_btn.clicked.connect(self._register_file_types)
        register_btn.setStyleSheet(
            "QPushButton { background-color: #161b22; color: #8b949e; border: 1px solid #30363d; "
            "border-radius: 6px; padding: 8px 16px; font-size: 12px; }"
            "QPushButton:hover { border-color: #58a6ff; color: #c9d1d9; }"
        )
        layout.addWidget(register_btn)

        return tab

    def _build_slideshow_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 20, 12, 12)
        layout.setSpacing(16)

        desc = QLabel("Auto-advance through images and videos in a folder.\nVideos play fully before advancing.")
        desc.setObjectName("subtitle")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QVBoxLayout()
        form.setSpacing(10)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Interval:"))
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 120)
        self._interval_spin.setValue(config.get("slideshow_interval", 5))
        self._interval_spin.setSuffix(" seconds")
        self._interval_spin.setMinimumWidth(120)
        row1.addWidget(self._interval_spin)
        row1.addStretch()
        form.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Order:"))
        self._order_combo = QComboBox()
        self._order_combo.addItems(["Sequential", "Random"])
        if config.get("slideshow_order", "sequential") == "random":
            self._order_combo.setCurrentIndex(1)
        self._order_combo.setMinimumWidth(120)
        row2.addWidget(self._order_combo)
        row2.addStretch()
        form.addLayout(row2)

        layout.addLayout(form)

        slide_btn = QPushButton("Pick Folder & Start Slideshow")
        slide_btn.setObjectName("accent")
        slide_btn.clicked.connect(self._start_slideshow)
        layout.addWidget(slide_btn)

        layout.addStretch()

        hint = QLabel("Shortcuts:  Space = pause  |  Arrows = prev/next  |  Esc = close")
        hint.setObjectName("subtitle")
        layout.addWidget(hint)

        return tab

    def _build_tools_tab(self):
        from PySide6.QtWidgets import QScrollArea
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # Unzip section
        unzip_group = QGroupBox("Auto-Unzip")
        unzip_layout = QVBoxLayout(unzip_group)
        unzip_layout.setSpacing(8)

        unzip_desc = QLabel("Extract all ZIP files in a folder into subfolders.")
        unzip_desc.setObjectName("subtitle")
        unzip_desc.setWordWrap(True)
        unzip_layout.addWidget(unzip_desc)

        checks_row = QHBoxLayout()
        self._recursive_check = QCheckBox("Search subfolders")
        checks_row.addWidget(self._recursive_check)
        self._delete_check = QCheckBox("Delete ZIPs after")
        checks_row.addWidget(self._delete_check)
        checks_row.addStretch()
        unzip_layout.addLayout(checks_row)

        checks_row2 = QHBoxLayout()
        self._unzip_flatten_check = QCheckBox("Flatten after (prefix folder names, delete folders & ZIPs)")
        self._unzip_flatten_check.setToolTip(
            "After extracting, moves all media into the root folder with folder-name prefixes, "
            "then deletes the empty subfolders and original ZIP files."
        )
        checks_row2.addWidget(self._unzip_flatten_check)
        checks_row2.addStretch()
        unzip_layout.addLayout(checks_row2)

        unzip_btn_row = QHBoxLayout()
        unzip_btn = QPushButton("Pick Folder & Unzip")
        unzip_btn.setObjectName("accent")
        unzip_btn.clicked.connect(self._unzip_folder)
        unzip_btn_row.addWidget(unzip_btn)
        unzip_btn_row.addStretch()
        unzip_layout.addLayout(unzip_btn_row)

        self._unzip_progress = QProgressBar()
        self._unzip_progress.setVisible(False)
        self._unzip_progress.setMaximumHeight(20)
        unzip_layout.addWidget(self._unzip_progress)

        layout.addWidget(unzip_group)

        # Flatten section
        flatten_group = QGroupBox("Flatten Folder")
        flatten_layout = QVBoxLayout(flatten_group)
        flatten_layout.setSpacing(8)

        flatten_desc = QLabel("Move all images and videos from subfolders into the selected folder. "
                              "Empty subfolders are removed afterwards.")
        flatten_desc.setObjectName("subtitle")
        flatten_desc.setWordWrap(True)
        flatten_layout.addWidget(flatten_desc)

        self._flatten_prefix_check = QCheckBox("Prefix filenames with folder name")
        self._flatten_prefix_check.setChecked(True)
        flatten_layout.addWidget(self._flatten_prefix_check)

        self._flatten_delete_check = QCheckBox("Delete empty subfolders after")
        self._flatten_delete_check.setChecked(True)
        flatten_layout.addWidget(self._flatten_delete_check)

        flatten_btn_row = QHBoxLayout()
        flatten_btn = QPushButton("Pick Folder & Flatten")
        flatten_btn.setObjectName("accent")
        flatten_btn.clicked.connect(self._flatten_folder)
        flatten_btn_row.addWidget(flatten_btn)
        flatten_btn_row.addStretch()
        flatten_layout.addLayout(flatten_btn_row)

        self._flatten_progress = QProgressBar()
        self._flatten_progress.setVisible(False)
        self._flatten_progress.setMaximumHeight(20)
        flatten_layout.addWidget(self._flatten_progress)

        layout.addWidget(flatten_group)

        layout.addStretch()

        hint = QLabel("Boss Key:  Ctrl+`  hides all windows instantly")
        hint.setObjectName("subtitle")
        layout.addWidget(hint)

        scroll.setWidget(content)
        tab_layout.addWidget(scroll)
        return tab

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.x()
        y = (screen.height() - self.height()) // 2 + screen.y()
        self.move(x, y)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip("RFab Viewer")
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show / Hide")
        show_action.triggered.connect(self._boss_key.toggle)
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._boss_key.toggle()

    # --- File handling ---

    def _handle_dropped(self, paths):
        files = []
        for p in paths:
            if p.is_dir():
                files.extend(get_media_files(p))
                config.add_recent_folder(p)
                self._refresh_recents()
            elif is_archive(p):
                self._unzip_single(p)
            elif is_media(p):
                files.append(p)

        if not files:
            return

        if len(files) == 1:
            self._open_single(files[0], files)
        else:
            self._open_as_grid(files)

    def _open_single(self, file_path, file_list=None):
        file_path = Path(file_path)
        if is_image(file_path):
            viewer = ImageViewer(file_path, file_list=file_list)
            viewer.request_slideshow.connect(lambda: self._start_slideshow_from_viewer(viewer))
            viewer.request_grid.connect(lambda: self._open_grid_from_viewer(viewer))
            self._track_window(viewer)
            viewer.show()
        elif is_video(file_path):
            player = VideoPlayer(file_path, file_list=file_list, loop=True)
            self._track_window(player)
            player.show()

    def _track_window(self, window):
        self._viewers.append(window)
        self._boss_key.register_window(window)
        window.closed.connect(lambda: self._remove_viewer(window))

    def _remove_viewer(self, window):
        if window in self._viewers:
            self._viewers.remove(window)
        # If launcher is hidden and all viewers are closed, quit after a brief delay
        # (delay allows IPC-delivered files to open before we decide to exit)
        if not self._viewers and not self.isVisible():
            QTimer.singleShot(500, self._maybe_quit)

    def _maybe_quit(self):
        from peek.resizable import ResizeMixin
        if not self._viewers and not self.isVisible() and not ResizeMixin._all_viewers:
            QApplication.quit()

    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder:
            folder = Path(folder)
            config.add_recent_folder(folder)
            self._refresh_recents()
            files = get_media_files(folder)
            if files:
                self._open_as_grid(files)

    def _open_grid(self):
        exts = " ".join(f"*{e}" for e in sorted(IMAGE_EXTENSIONS | VIDEO_EXTENSIONS))
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "",
            f"Media Files ({exts});;All Files (*)"
        )
        if files:
            paths = [Path(f) for f in files]
            if len(paths) == 1:
                self._open_single(paths[0])
            else:
                self._open_as_grid(paths)

    def _open_as_grid(self, files):
        grid = GridView([str(f) for f in files], max_columns=config.get("grid_max_columns", 4))
        grid.cell_clicked.connect(self._on_grid_cell_clicked)
        self._track_window(grid)
        grid.show()

    def _on_grid_cell_clicked(self, index, file_path):
        self._open_single(Path(file_path))

    def _open_grid_from_viewer(self, viewer):
        if viewer._file_list:
            grid = GridView([str(f) for f in viewer._file_list], max_columns=config.get("grid_max_columns", 4))
            grid.cell_clicked.connect(self._on_grid_cell_clicked)
            self._track_window(grid)
            grid.show()

    # --- Slideshow ---

    def _start_slideshow(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder for Slideshow")
        if not folder:
            return
        folder = Path(folder)
        files = get_media_files(folder)
        if not files:
            return

        config.add_recent_folder(folder)
        self._refresh_recents()

        interval = self._interval_spin.value()
        order = "random" if self._order_combo.currentIndex() == 1 else "sequential"
        config.set("slideshow_interval", interval)
        config.set("slideshow_order", order)

        show = SlideshowView([str(f) for f in files], interval=interval, order=order)
        self._track_window(show)
        show.show()

    def _start_slideshow_from_viewer(self, viewer):
        if viewer._file_list:
            interval = self._interval_spin.value()
            order = "random" if self._order_combo.currentIndex() == 1 else "sequential"
            show = SlideshowView(
                [str(f) for f in viewer._file_list],
                interval=interval,
                order=order,
            )
            self._track_window(show)
            show.show()

    # --- Unzip ---

    def _unzip_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Unzip")
        if not folder:
            return

        recursive = self._recursive_check.isChecked()
        delete_after = self._delete_check.isChecked()
        flatten_after = self._unzip_flatten_check.isChecked()

        # If flatten-after is on, we always delete ZIPs (no separate confirmation needed)
        if flatten_after:
            delete_after = True
        elif delete_after:
            reply = QMessageBox.question(
                self, "Confirm Delete",
                "Delete ZIP files after extraction?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        archives = get_archive_files(folder, recursive=recursive)
        if not archives:
            QMessageBox.information(self, "No Archives", "No ZIP files found in this folder.")
            return

        self._unzip_progress.setMaximum(len(archives))
        self._unzip_progress.setValue(0)
        self._unzip_progress.setVisible(True)

        def on_progress(current, total, name, status):
            self._unzip_progress.setValue(current)
            self._unzip_progress.setFormat(f"{name} ({current}/{total})")
            QApplication.processEvents()

        # Step 1: Unzip all archives (delete ZIPs after if requested)
        results = unzip_folder(folder, recursive=recursive, delete_after=delete_after, progress_callback=on_progress)

        self._unzip_progress.setVisible(False)

        if flatten_after:
            # Step 2: Flatten — move all media from subfolders to root, prefix with folder name
            from peek.utils import flatten_folder
            flatten_results = flatten_folder(
                folder, delete_empty=True, prefix_folder=True, progress_callback=None
            )
            # Step 3: Delete any remaining ZIPs that were skipped
            remaining_zips = get_archive_files(folder, recursive=recursive)
            for arc in remaining_zips:
                try:
                    Path(arc).unlink()
                except Exception:
                    pass
            msg = (
                f"Done! (Unzipped & Flattened)\n\n"
                f"Extracted: {results['success']} archives\n"
                f"Skipped: {results['skipped']}\n"
                f"Flattened: {flatten_results['moved']} files\n"
                f"Folders removed: {flatten_results['removed_dirs']}"
            )
        else:
            msg = f"Done!\n\nExtracted: {results['success']}\nSkipped: {results['skipped']}\nFailed: {results['failed']}"
        QMessageBox.information(self, "Unzip Complete", msg)

    def _unzip_single(self, archive_path):
        from peek.unzipper import unzip_folder as _unzip
        import zipfile
        archive_path = Path(archive_path)
        extract_dir = archive_path.parent / archive_path.stem
        try:
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)
            files = get_media_files(extract_dir)
            if files:
                self._open_single(files[0], files)
        except Exception as e:
            QMessageBox.warning(self, "Unzip Error", str(e))

    # --- Flatten ---

    def _flatten_folder(self):
        from peek.utils import flatten_folder
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Flatten")
        if not folder:
            return

        # Count media in subfolders first
        folder_path = Path(folder)
        media_in_subs = [
            f for f in folder_path.rglob("*")
            if f.is_file() and f.parent != folder_path and f.suffix.lower() in (
                {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif",
                 ".mp4", ".webm", ".avi", ".mkv", ".mov"})
        ]
        if not media_in_subs:
            QMessageBox.information(self, "Nothing to Flatten", "No media files found in subfolders.")
            return

        reply = QMessageBox.question(
            self, "Flatten Folder",
            f"Move {len(media_in_subs)} media files from subfolders into:\n{folder}\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        delete_empty = self._flatten_delete_check.isChecked()
        prefix_folder = self._flatten_prefix_check.isChecked()

        self._flatten_progress.setMaximum(len(media_in_subs))
        self._flatten_progress.setValue(0)
        self._flatten_progress.setVisible(True)

        def on_progress(name, current, total):
            self._flatten_progress.setValue(current)
            self._flatten_progress.setFormat(f"{name} ({current}/{total})")
            QApplication.processEvents()

        results = flatten_folder(folder, delete_empty=delete_empty, prefix_folder=prefix_folder, progress_callback=on_progress)

        self._flatten_progress.setVisible(False)

        msg = (f"Done!\n\nMoved: {results['moved']}\nFailed: {results['failed']}")
        if delete_empty:
            msg += f"\nEmpty folders removed: {results['removed_dirs']}"
        QMessageBox.information(self, "Flatten Complete", msg)

    # --- File association ---

    def _register_file_types(self):
        if sys.platform != "win32":
            QMessageBox.information(self, "macOS", "Right-click a file → Get Info → Open with → select RFab Viewer → Change All.")
            return

        import winreg
        app_name = "RFabViewer"

        # Find the exe or python command
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller exe — sys.executable IS the exe
            command = f'"{sys.executable}" "%1"'
        else:
            # Running from source — check for built exe first (onedir layout)
            script_dir = Path(__file__).resolve().parent.parent
            exe_path = script_dir / "dist" / "RFab Viewer" / "RFab Viewer.exe"
            if not exe_path.exists():
                exe_path = script_dir / "dist" / "RFab Viewer.exe"
            if exe_path.exists():
                command = f'"{exe_path}" "%1"'
            else:
                main_py = script_dir / "main.py"
                command = f'"{sys.executable}" "{main_py}" "%1"'

        try:
            classes = winreg.HKEY_CURRENT_USER

            with winreg.CreateKey(classes, f"Software\\Classes\\{app_name}") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "RFab Viewer")
            with winreg.CreateKey(classes, f"Software\\Classes\\{app_name}\\shell\\open\\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)

            all_exts = list(IMAGE_EXTENSIONS) + list(VIDEO_EXTENSIONS)
            for ext in all_exts:
                with winreg.CreateKey(classes, f"Software\\Classes\\{ext}\\OpenWithProgids") as key:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, "")
                with winreg.CreateKey(classes, f"Software\\Classes\\{ext}") as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, app_name)

            QMessageBox.information(
                self, "Registered",
                f"RFab Viewer registered for {len(all_exts)} file types.\n\n"
                "Double-click any image or video to open it in RFab Viewer.\n"
                "You may need to restart Explorer for changes to take effect."
            )
        except Exception as e:
            QMessageBox.warning(self, "Registration Failed", str(e))

    # --- Window events ---

    def closeEvent(self, event):
        for viewer in list(self._viewers):
            try:
                viewer.close()
            except RuntimeError:
                pass
        super().closeEvent(event)


_IPC_PORT = 52184  # local port for single-instance communication


def _try_send_to_existing(files):
    """Try to send file paths to an already-running instance. Returns True if successful."""
    import socket, json
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        sock.connect(('127.0.0.1', _IPC_PORT))
        # Grant the existing instance permission to take foreground
        if sys.platform == 'win32':
            try:
                import ctypes
                # ASFW_ANY = -1 allows any process to set foreground
                ctypes.windll.user32.AllowSetForegroundWindow(-1)
            except Exception:
                pass
        sock.sendall(json.dumps([str(f) for f in files]).encode('utf-8'))
        # Wait for confirmation
        reply = sock.recv(16)
        sock.close()
        return reply == b'OK'
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


class _IPCBridge(QObject):
    """Bridge that receives signals from the IPC thread and opens files on the main thread."""
    files_received = Signal(list)

    def __init__(self, launcher):
        super().__init__()
        self._launcher = launcher
        self.files_received.connect(self._open_files)

    def _open_files(self, files):
        if len(files) == 1:
            self._launcher._open_single(files[0])
        elif files:
            self._launcher._open_as_grid(files)
        # Bring the newest viewer to front (force foreground on Windows)
        if self._launcher._viewers:
            w = self._launcher._viewers[-1]
            w.setWindowState(w.windowState() & ~Qt.WindowState.WindowMinimized)
            w.raise_()
            w.activateWindow()
            if sys.platform == 'win32':
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    hwnd = int(w.winId())
                    # Attach to foreground thread to gain permission
                    fg_hwnd = user32.GetForegroundWindow()
                    fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
                    my_tid = ctypes.windll.kernel32.GetCurrentThreadId()
                    if fg_tid != my_tid:
                        user32.AttachThreadInput(fg_tid, my_tid, True)
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                    if fg_tid != my_tid:
                        user32.AttachThreadInput(fg_tid, my_tid, False)
                except Exception:
                    pass


class _IPCServer:
    """Listens for file paths from new instances."""

    def __init__(self, launcher):
        import socket, threading
        self._bridge = _IPCBridge(launcher)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.bind(('127.0.0.1', _IPC_PORT))
        except OSError:
            self._sock = None
            return
        self._sock.listen(5)
        self._sock.settimeout(1.0)
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _listen(self):
        import json
        while self._running:
            try:
                conn, _ = self._sock.accept()
                data = conn.recv(65536).decode('utf-8')
                if data:
                    files = [Path(p) for p in json.loads(data)]
                    self._bridge.files_received.emit(files)
                    conn.sendall(b'OK')
                conn.close()
            except (OSError, TimeoutError):
                pass

    def stop(self):
        self._running = False
        if self._sock:
            self._sock.close()


def main():
    import traceback, tempfile, os
    log_path = Path(tempfile.gettempdir()) / "rfab_viewer.log"

    # Configure Python logging module with immediate flush
    import logging
    _handler = logging.FileHandler(str(log_path), mode='a', encoding='utf-8')
    _handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s', '%H:%M:%S'))
    _handler.setLevel(logging.DEBUG)
    # Force flush on every emit
    _orig_emit = _handler.emit
    def _flush_emit(record):
        _orig_emit(record)
        _handler.flush()
    _handler.emit = _flush_emit
    logging.root.addHandler(_handler)
    logging.root.setLevel(logging.DEBUG)
    # Suppress noisy PIL debug
    logging.getLogger('PIL').setLevel(logging.WARNING)

    try:
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"\n--- Launch: {sys.argv}\n")

        # Handle files passed via command-line (e.g. "Open With" from Explorer)
        # Try individual args first, then try joining all args as one path (spaces in path)
        cli_files = [Path(a) for a in sys.argv[1:] if Path(a).is_file() and is_media(a)]
        if not cli_files and len(sys.argv) > 1:
            joined = " ".join(sys.argv[1:])
            p = Path(joined)
            if p.is_file() and is_media(p):
                cli_files = [p]

        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"cli_files: {cli_files}\n")

        # Single-instance: if files given and another instance is running, hand off to it
        if cli_files and _try_send_to_existing(cli_files):
            with open(log_path, "a", encoding="utf-8") as log:
                log.write("Handed off to existing instance\n")
            return

        # Disable Qt auto DPI scaling to prevent segfault when moving between
        # monitors with different DPI/scale factors
        import os
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

        app = QApplication(sys.argv)
        app.setApplicationName("RFab Viewer")
        app.setStyleSheet(DARK_STYLE)

        # Set app-wide icon (applies to all windows)
        icon_path = Path(__file__).resolve().parent.parent / "peek.ico"
        if not icon_path.exists() and hasattr(sys, '_MEIPASS'):
            icon_path = Path(sys._MEIPASS) / "peek.ico"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        window = LauncherWindow()

        # Start IPC server so future instances send files here
        ipc = _IPCServer(window)

        if cli_files:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Opening viewer for: {cli_files}\n")
            if len(cli_files) == 1:
                window._open_single(cli_files[0])
            else:
                window._open_as_grid(cli_files)
        else:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write("Showing launcher\n")
            window.show()

        ret = app.exec()
        ipc.stop()
        sys.exit(ret)

    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"CRASH: {e}\n{traceback.format_exc()}\n")
        raise


if __name__ == "__main__":
    main()
