import zipfile
import logging
from pathlib import Path

from peek.utils import get_archive_files

_log = logging.getLogger('rfab_viewer')


def safe_extract_dir(archive_path):
    """Extraction folder for an archive, with a Windows-safe name.

    Windows silently strips trailing spaces/dots when creating a directory,
    so a ZIP named "Foo .zip" would extract into "Foo " -> mkdir creates
    "Foo" but the member paths still reference "Foo " and every file write
    fails with Errno 2. Strip trailing spaces/dots up front.
    """
    archive_path = Path(archive_path)
    name = archive_path.stem.rstrip(' .')
    if not name:
        name = "extracted"
    return archive_path.parent / name


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
        extract_dir = safe_extract_dir(archive_path)

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
                # Extract member-by-member so the progress callback can keep
                # the UI responsive on large archives (extractall blocks for
                # the whole archive and Windows flags the app as hung)
                members = zf.infolist()
                for j, member in enumerate(members):
                    zf.extract(member, extract_dir)
                    if progress_callback and j % 25 == 0:
                        progress_callback(i + 1, results["total"],
                                          f"{archive_path.name} ({j + 1}/{len(members)})",
                                          "extracting")

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
