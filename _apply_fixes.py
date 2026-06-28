"""Apply grid_view.py fixes: layout button visibility + arrow key navigation."""
import pathlib

p = pathlib.Path(r'C:\Users\Merry\dev\peek-viewer\peek\grid_view.py')
content = p.read_text(encoding='utf-8')

# Track what we change
changes = []

# 1. Add get_media_files to import
old = 'from peek.utils import is_image, is_video, fit_size'
new = 'from peek.utils import is_image, is_video, fit_size, get_media_files'
if old in content and new not in content:
    content = content.replace(old, new)
    changes.append('Added get_media_files import')

# 2. Add _focused_cell_idx init
old = "        self._resize_active = False\n        self._layout_mode = 'auto'  # 'auto', '1row', '2row'\n        self._resize_init()"
new = "        self._resize_active = False\n        self._layout_mode = 'auto'  # 'auto', '1row', '2row'\n        self._focused_cell_idx = None  # last clicked/interacted cell for navigation\n        self._resize_init()"
if old in content:
    content = content.replace(old, new)
    changes.append('Added _focused_cell_idx state')

# 3. Set default focused cell after init
old = "        # Hide remove button when only one cell (window X suffices)\n        if len(self._cells) == 1:\n            self._cells[0]._remove_btn.hide()\n\n    def _do_layout(self):"
new = "        # Hide remove button when only one cell (window X suffices)\n        if len(self._cells) == 1:\n            self._cells[0]._remove_btn.hide()\n        # Default focused cell to last cell\n        if self._cells:\n            self._focused_cell_idx = len(self._cells) - 1\n\n    def _do_layout(self):"
if old in content:
    content = content.replace(old, new)
    changes.append('Set default focused cell')

# 4. Add .show() to layout buttons
old = '''        auto_btn.clicked.connect(self._set_layout_auto)
        self._wc_buttons.insert(0, auto_btn)'''
new = '''        auto_btn.clicked.connect(self._set_layout_auto)
        auto_btn.show()
        self._wc_buttons.insert(0, auto_btn)'''
if old in content and 'auto_btn.show()' not in content:
    content = content.replace(old, new)
    changes.append('Added auto_btn.show()')

old = '''        row1_btn.clicked.connect(self._set_layout_1row)
        self._wc_buttons.insert(1, row1_btn)'''
new = '''        row1_btn.clicked.connect(self._set_layout_1row)
        row1_btn.show()
        self._wc_buttons.insert(1, row1_btn)'''
if old in content and 'row1_btn.show()' not in content:
    content = content.replace(old, new)
    changes.append('Added row1_btn.show()')

old = '''        row2_btn.clicked.connect(self._set_layout_2row)
        self._wc_buttons.insert(2, row2_btn)'''
new = '''        row2_btn.clicked.connect(self._set_layout_2row)
        row2_btn.show()
        self._wc_buttons.insert(2, row2_btn)'''
if old in content and 'row2_btn.show()' not in content:
    content = content.replace(old, new)
    changes.append('Added row2_btn.show()')

# 5. Update keyPressEvent
old = '''    def keyPressEvent(self, event):
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
            super().keyPressEvent(event)'''
new = '''    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        _log.info(f"GRID KEY: {key}")
        if key == Qt.Key.Key_Escape:
            if self._is_fullscreen:
                self._toggle_fullscreen()
            else:
                self.close()
        elif key == Qt.Key.Key_F:
            self._toggle_fullscreen()
        elif key == Qt.Key.Key_Left:
            if mods & Qt.KeyboardModifier.ControlModifier:
                self._max_columns = max(1, self._max_columns - 1)
                _log.info(f"GRID KEY CTRL+LEFT: max_columns now {self._max_columns}")
                self._do_layout()
            else:
                self._navigate_focused(-1)
        elif key == Qt.Key.Key_Right:
            if mods & Qt.KeyboardModifier.ControlModifier:
                self._max_columns = min(len(self._cells), self._max_columns + 1)
                _log.info(f"GRID KEY CTRL+RIGHT: max_columns now {self._max_columns}")
                self._do_layout()
            else:
                self._navigate_focused(1)
        else:
            super().keyPressEvent(event)'''
if old in content:
    content = content.replace(old, new)
    changes.append('Updated keyPressEvent for navigation')

# 6. Update mouseReleaseEvent in GridCell
old = '''    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            parent = self.parentWidget()
            if parent and hasattr(parent, '_end_cell_drag'):
                parent._end_cell_drag()

    def mouseDoubleClickEvent(self, event):'''
new = '''    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            parent = self.parentWidget()
            was_dragging = getattr(parent, '_dragging', False) if parent else False
            if parent and hasattr(parent, '_end_cell_drag'):
                parent._end_cell_drag()
            # Set this cell as focused if it wasn't a drag
            if not was_dragging and parent and hasattr(parent, '_set_focused_cell'):
                parent._set_focused_cell(self.index)

    def mouseDoubleClickEvent(self, event):'''
if old in content:
    content = content.replace(old, new)
    changes.append('Updated mouseReleaseEvent for focus')

# 7. Update _add_files to set focus
old = '''    def _add_files(self, new_files):
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
        self._do_layout()'''
new = '''    def _add_files(self, new_files):
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
        # Focus the last added cell
        if self._cells:
            self._set_focused_cell(len(self._cells) - 1)
        self._do_layout()'''
if old in content:
    content = content.replace(old, new)
    changes.append('Updated _add_files to set focus')

# 8. Add navigation methods before dragEnterEvent
nav_methods = '''
    def _set_focused_cell(self, index):
        """Set the focused cell and update visual indicator."""
        if index < 0 or index >= len(self._cells):
            return
        old_idx = self._focused_cell_idx
        self._focused_cell_idx = index
        # Remove highlight from old focused cell
        if old_idx is not None and 0 <= old_idx < len(self._cells):
            self._cells[old_idx].setStyleSheet("background-color: black;")
        # Highlight new focused cell
        self._cells[index].setStyleSheet(
            "background-color: black; border: 1px solid rgba(88, 166, 255, 0.5);"
        )

    def _navigate_focused(self, delta):
        """Navigate the focused cell to the next/prev file in its directory."""
        if not self._cells:
            return
        idx = self._focused_cell_idx
        if idx is None or idx < 0 or idx >= len(self._cells):
            idx = len(self._cells) - 1
            self._focused_cell_idx = idx

        cell = self._cells[idx]
        current_path = cell.file_path
        parent_dir = current_path.parent

        # Get sorted media files in the same directory
        siblings = get_media_files(parent_dir)
        if not siblings:
            return

        # Find current position in directory listing
        try:
            pos = [str(f) for f in siblings].index(str(current_path))
        except ValueError:
            pos = 0

        new_pos = (pos + delta) % len(siblings)
        new_path = siblings[new_pos]

        if new_path == current_path:
            return

        # Update the cell with the new file
        self._replace_cell_file(idx, new_path)

    def _replace_cell_file(self, cell_idx, new_path):
        """Replace the file displayed in a cell with a new file."""
        new_path = Path(new_path)
        cell = self._cells[cell_idx]

        # Cleanup old media
        cell.cleanup()
        if hasattr(cell, '_label'):
            cell._label.deleteLater()
            del cell._label
        if hasattr(cell, '_video_widget'):
            cell._video_widget.deleteLater()
            del cell._video_widget
        cell._pixmap = None
        cell._movie = None
        cell._player = None
        cell._audio = None

        # Update file path and aspect
        cell.file_path = new_path
        new_aspect = _get_aspect(new_path)
        cell.aspect = new_aspect
        self.file_paths[cell_idx] = new_path
        self._aspects[cell_idx] = new_aspect

        # Setup new media
        if is_image(new_path):
            cell._setup_image()
        elif is_video(new_path):
            cell._setup_video()

        # Re-layout and render content at current cell size
        self._do_layout()
        w, h = cell.width(), cell.height()
        if hasattr(cell, '_label'):
            cell._label.setGeometry(0, 0, w, h)
            if getattr(cell, '_movie', None):
                from PySide6.QtCore import QSize
                cell._movie.setScaledSize(QSize(w, h))
            elif cell._pixmap:
                fw, fh = fit_size(cell._pixmap.width(), cell._pixmap.height(), w, h)
                scaled = cell._pixmap.scaled(fw, fh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                cell._label.setPixmap(scaled)
        if hasattr(cell, '_video_widget'):
            cell._video_widget.setGeometry(0, 0, w, h)

'''

marker = '    def dragEnterEvent(self, event: QDragEnterEvent):'
if marker in content and '_set_focused_cell' not in content:
    content = content.replace(marker, nav_methods + marker)
    changes.append('Added navigation methods (_set_focused_cell, _navigate_focused, _replace_cell_file)')

# Write back
p.write_text(content, encoding='utf-8')
print(f'Applied {len(changes)} changes:')
for c in changes:
    print(f'  - {c}')
