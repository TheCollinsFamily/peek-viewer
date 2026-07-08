import zipfile
import logging
from pathlib import Path

from peek.utils import get_archive_files

_log = logging.getLogger('rfab_viewer')


def unzip_folder(folder_path, recursive=False, delete_after=False, progress_callback=None):
    folder = Path(folder_path)
    archives = get_archive_files(folder, recursive=recursive)
    _log.info(f"UNZIP: Starting extraction of {len(archives)} archives in '{folder}' (recursive={recursive}, delete_after={delete_after})")

    results = {
        "total": len(archives),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "failed_archives": [],  # track which archives failed
        "details": [],
    }

    for i, archive_path in enumerate(archives):
        archive_path = Path(archive_path)
        extract_dir = archive_path.parent / archive_path.stem

        if extract_dir.exists() and any(extract_dir.iterdir()):
            results["skipped"] += 1
            results["details"].append({
                "file": archive_path.name,
                "status": "skipped",
                "reason": "Already extracted",
            })
            _log.info(f"UNZIP: Skipped '{archive_path.name}' (already extracted to '{extract_dir}')")
            if progress_callback:
                progress_callback(i + 1, results["total"], archive_path.name, "skipped")
            continue

        try:
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)

            file_count = len(list(extract_dir.rglob("*")))
            results["success"] += 1
            results["details"].append({
                "file": archive_path.name,
                "status": "success",
                "extracted_to": str(extract_dir),
                "file_count": file_count,
            })
            _log.info(f"UNZIP: OK '{archive_path.name}' -> {file_count} files in '{extract_dir}'")

            if delete_after:
                archive_path.unlink()
                _log.info(f"UNZIP: Deleted source archive '{archive_path.name}'")

        except Exception as e:
            results["failed"] += 1
            results["failed_archives"].append(str(archive_path))
            results["details"].append({
                "file": archive_path.name,
                "status": "failed",
                "error": str(e),
            })
            _log.error(f"UNZIP: FAILED '{archive_path.name}': {e}")

        if progress_callback:
            progress_callback(i + 1, results["total"], archive_path.name, "done")

    return results
