"""Add navigation method definitions before dragEnterEvent."""
import pathlib

p = pathlib.Path(r'C:\Users\Merry\dev\peek-viewer\peek\grid_view.py')
content = p.read_text(encoding='utf-8')

nav_methods = '''    def _set_focused_cell(self, index):
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
if marker in content and 'def _set_focused_cell' not in content:
    content = content.replace(marker, nav_methods + marker)
    p.write_text(content, encoding='utf-8')
    print('Added navigation methods')
else:
    print(f'marker found: {marker in content}')
    print(f'def _set_focused_cell found: {"def _set_focused_cell" in content}')
