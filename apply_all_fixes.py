"""Apply ALL pending fixes to grid_view.py and image_viewer.py."""

# === Fix grid_view.py ===
path = r'C:\Users\Merry\dev\peek-viewer\peek\grid_view.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add _resize_active and _layout_mode to __init__
old = "        self._resize_init()\n        self.setAcceptDrops(True)"
new = "        self._resize_active = False\n        self._layout_mode = 'auto'  # 'auto', '1row', '2row'\n        self._resize_init()\n        self.setAcceptDrops(True)"
if '_resize_active' not in content:
    content = content.replace(old, new)
    print("OK grid: _resize_active + _layout_mode added")

# 2. Add _add_layout_buttons() call after _create_fullscreen_btn()
old2 = "        self._create_fullscreen_btn()\n        self._do_layout()"
new2 = "        self._create_fullscreen_btn()\n        self._add_layout_buttons()\n        self._do_layout()"
if '_add_layout_buttons' not in content:
    content = content.replace(old2, new2)
    print("OK grid: _add_layout_buttons call added")

# 3. Fix mousePressEvent
old3 = """    def mousePressEvent(self, event):
        if self._resize_mouse_press(event):
            return
        super().mousePressEvent(event)"""
new3 = """    def mousePressEvent(self, event):
        if self._resize_mouse_press(event):
            self._resize_active = True
            return
        super().mousePressEvent(event)"""
if 'self._resize_active = True' not in content:
    content = content.replace(old3, new3)
    print("OK grid: mousePressEvent patched")

# 4. Fix mouseReleaseEvent + add _finalize_resize
old4 = """    def mouseReleaseEvent(self, event):
        self._resize_mouse_release(event)"""
new4 = """    def mouseReleaseEvent(self, event):
        was_resizing = self._resize_active
        self._resize_active = False
        self._resize_mouse_release(event)
        if was_resizing:
            self._finalize_resize()

    def _finalize_resize(self):
        \"\"\"Force one final smooth-quality render after resize completes.\"\"\"
        for cell in self._cells:
            if hasattr(cell, '_label') and hasattr(cell, '_pixmap') and cell._pixmap:
                w, h = cell.width(), cell.height()
                fw, fh = fit_size(cell._pixmap.width(), cell._pixmap.height(), w, h)
                scaled = cell._pixmap.scaled(fw, fh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                cell._label.setPixmap(scaled)"""
if '_finalize_resize' not in content:
    content = content.replace(old4, new4)
    print("OK grid: mouseReleaseEvent + _finalize_resize added")

# 5. Add layout methods and _add_layout_buttons after _toggle_fullscreen
old5 = """    def _toggle_fullscreen(self):
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._is_fullscreen = True

    def dragEnterEvent"""
new5 = """    def _toggle_fullscreen(self):
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._is_fullscreen = True

    def _add_layout_buttons(self):
        \"\"\"Add layout mode buttons (auto grid / 1 row / 2 rows) to the button bar.\"\"\"
        from peek.resizable import _WC_BTN_STYLE
        if not self._btn_bar:
            return

        auto_btn = QPushButton("\\u25a6", self._btn_bar)
        auto_btn.setFixedSize(28, 28)
        auto_btn.setStyleSheet(_WC_BTN_STYLE)
        auto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        auto_btn.setToolTip("Auto grid layout")
        auto_btn.clicked.connect(self._set_layout_auto)
        self._wc_buttons.insert(0, auto_btn)

        row1_btn = QPushButton("\\u25ac", self._btn_bar)
        row1_btn.setFixedSize(28, 28)
        row1_btn.setStyleSheet(_WC_BTN_STYLE)
        row1_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row1_btn.setToolTip("Single row layout")
        row1_btn.clicked.connect(self._set_layout_1row)
        self._wc_buttons.insert(1, row1_btn)

        row2_btn = QPushButton("\\u2261", self._btn_bar)
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

    def dragEnterEvent"""
if '_add_layout_buttons' not in content or '_set_layout_auto' not in content:
    content = content.replace(old5, new5)
    print("OK grid: layout buttons + methods added")

# 6. Skip scaling during resize in GridCell.resizeEvent
old6 = """            elif self._pixmap:
                fw, fh = fit_size(self._pixmap.width(), self._pixmap.height(), w, h)
                scaled = self._pixmap.scaled(fw, fh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self._label.setPixmap(scaled)"""
new6 = """            elif self._pixmap:
                # Skip scaling entirely during active resize for smooth drag
                parent = self.parentWidget()
                if getattr(parent, '_resize_active', False):
                    return
                fw, fh = fit_size(self._pixmap.width(), self._pixmap.height(), w, h)
                scaled = self._pixmap.scaled(fw, fh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self._label.setPixmap(scaled)"""
if "getattr(parent, '_resize_active'" not in content:
    content = content.replace(old6, new6)
    print("OK grid: skip scaling during resize")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("grid_view.py saved\n")

# === Fix image_viewer.py ===
path2 = r'C:\Users\Merry\dev\peek-viewer\peek\image_viewer.py'
with open(path2, 'r', encoding='utf-8') as f:
    content2 = f.read()

# 1. Add WA_TransparentForMouseEvents to label
old_iv1 = "        self._label = QLabel(self)\n        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)\n        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)"
new_iv1 = "        self._label = QLabel(self)\n        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)\n        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)\n        self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)"
if 'WA_TransparentForMouseEvents' not in content2:
    content2 = content2.replace(old_iv1, new_iv1)
    print("OK image: WA_TransparentForMouseEvents added")

# 2. Skip rendering during resize in resizeEvent
old_iv2 = """    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_fs_btn()
        self._raise_grab_handle()
        if self._movie:
            from PySide6.QtCore import QSize
            w, h = self.width(), self.height()
            self._label.setGeometry(0, 0, w, h)
            self._movie.setScaledSize(QSize(w, h))
        else:
            self._render()"""
new_iv2 = """    def resizeEvent(self, event):
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
            self._render()"""
if "getattr(self, '_resize_active'" not in content2:
    content2 = content2.replace(old_iv2, new_iv2)
    print("OK image: resizeEvent skip during resize")

# 3. Set _resize_active in mousePressEvent
old_iv3 = """    def mousePressEvent(self, event):
        if self._resize_mouse_press(event):
            return
        if event.button() == Qt.MouseButton.LeftButton:"""
new_iv3 = """    def mousePressEvent(self, event):
        if self._resize_mouse_press(event):
            self._resize_active = True
            return
        if event.button() == Qt.MouseButton.LeftButton:"""
if 'self._resize_active = True' not in content2:
    content2 = content2.replace(old_iv3, new_iv3)
    print("OK image: mousePressEvent patched")

# 4. Clear _resize_active and render on release
old_iv4 = """    def mouseReleaseEvent(self, event):
        if self._resize_mouse_release(event):
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None"""
new_iv4 = """    def mouseReleaseEvent(self, event):
        was_resizing = getattr(self, '_resize_active', False)
        self._resize_active = False
        if self._resize_mouse_release(event):
            if was_resizing:
                self._render()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None"""
if "was_resizing = getattr(self, '_resize_active'" not in content2:
    content2 = content2.replace(old_iv4, new_iv4)
    print("OK image: mouseReleaseEvent patched")

with open(path2, 'w', encoding='utf-8') as f:
    f.write(content2)
print("image_viewer.py saved\n")
print("ALL DONE")
