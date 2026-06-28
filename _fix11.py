"""Fix: rewrite _unzip_folder so 'Flatten after' always works end-to-end."""
import pathlib

p = pathlib.Path(r'C:\Users\Merry\.windsurf\Reality Fabricator\peek-viewer\peek\main.py')
content = p.read_text(encoding='utf-8')

old = '''    def _unzip_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Unzip")
        if not folder:
            return

        recursive = self._recursive_check.isChecked()
        delete_after = self._delete_check.isChecked()

        if delete_after:
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

        results = unzip_folder(folder, recursive=recursive, delete_after=delete_after, progress_callback=on_progress)

        self._unzip_progress.setVisible(False)

        # If flatten-after is checked, run flatten then cleanup
        flatten_after = self._unzip_flatten_check.isChecked()
        if flatten_after and results['success'] > 0:
            from peek.utils import flatten_folder
            flatten_results = flatten_folder(
                folder, delete_empty=True, prefix_folder=True, progress_callback=None
            )
            # Delete original ZIPs if not already deleted
            if not delete_after:
                from peek.utils import get_archive_files
                for arc in get_archive_files(folder, recursive=recursive):
                    try:
                        Path(arc).unlink()
                    except Exception:
                        pass
            msg = (
                f"Done! (Unzipped & Flattened)\\n\\n"
                f"Extracted: {results['success']}\\n"
                f"Flattened: {flatten_results['moved']} files\\n"
                f"Folders removed: {flatten_results['removed_dirs']}"
            )
        else:
            msg = f"Done!\\n\\nExtracted: {results['success']}\\nSkipped: {results['skipped']}\\nFailed: {results['failed']}"
        QMessageBox.information(self, "Unzip Complete", msg)'''

new = '''    def _unzip_folder(self):
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
                f"Done! (Unzipped & Flattened)\\n\\n"
                f"Extracted: {results['success']} archives\\n"
                f"Skipped: {results['skipped']}\\n"
                f"Flattened: {flatten_results['moved']} files\\n"
                f"Folders removed: {flatten_results['removed_dirs']}"
            )
        else:
            msg = f"Done!\\n\\nExtracted: {results['success']}\\nSkipped: {results['skipped']}\\nFailed: {results['failed']}"
        QMessageBox.information(self, "Unzip Complete", msg)'''

if old in content:
    content = content.replace(old, new)
    p.write_text(content, encoding='utf-8')
    print('Fixed: _unzip_folder rewritten - flatten always runs when checked')
else:
    print('ERROR: pattern not found')
