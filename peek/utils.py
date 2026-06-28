from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".avi", ".mkv", ".mov"}
ARCHIVE_EXTENSIONS = {".zip"}
ALL_MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def is_image(path):
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def is_video(path):
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def is_media(path):
    return Path(path).suffix.lower() in ALL_MEDIA_EXTENSIONS


def is_archive(path):
    return Path(path).suffix.lower() in ARCHIVE_EXTENSIONS


def get_media_files(folder_path, sort=True):
    folder = Path(folder_path)
    if not folder.is_dir():
        return []
    files = [f for f in folder.iterdir() if f.is_file() and is_media(f)]
    if sort:
        files.sort(key=lambda f: natural_sort_key(f.name))
    return files


def get_archive_files(folder_path, recursive=False):
    folder = Path(folder_path)
    if not folder.is_dir():
        return []
    if recursive:
        return [f for f in folder.rglob("*") if f.is_file() and is_archive(f)]
    return [f for f in folder.iterdir() if f.is_file() and is_archive(f)]


def natural_sort_key(text):
    import re
    parts = re.split(r"(\d+)", str(text))
    result = []
    for part in parts:
        if part.isdigit():
            result.append((0, int(part)))
        else:
            result.append((1, part.lower()))
    return result


def flatten_folder(folder_path, delete_empty=True, prefix_folder=False, progress_callback=None):
    """Move all media files from subfolders into the root folder.

    If prefix_folder is True, prepend the immediate subfolder name to each
    filename (e.g. "subfolder - image.jpg") so files sort by origin.

    Returns dict with counts: moved, skipped, failed, removed_dirs.
    """
    import shutil, os
    folder = Path(folder_path)
    if not folder.is_dir():
        return {"moved": 0, "skipped": 0, "failed": 0, "removed_dirs": 0}

    # Collect all media in subfolders (not already in root)
    media_files = [
        f for f in folder.rglob("*")
        if f.is_file() and is_media(f) and f.parent != folder
    ]

    moved = 0
    skipped = 0
    failed = 0
    total = len(media_files)

    for i, src in enumerate(media_files):
        # Preserve original timestamps before move
        try:
            orig_stat = src.stat()
            orig_mtime = orig_stat.st_mtime
            orig_atime = orig_stat.st_atime
        except Exception:
            orig_mtime = orig_atime = None

        # Build destination name
        if prefix_folder:
            # Use the immediate parent folder's name relative to root
            rel = src.parent.relative_to(folder)
            prefix = str(rel).replace(os.sep, " - ") + " - "
            base_name = prefix + src.name
        else:
            base_name = src.name

        dst = folder / base_name
        # Handle name collisions
        if dst.exists():
            stem = dst.stem
            suffix = dst.suffix
            counter = 1
            while dst.exists():
                dst = folder / f"{stem}_{counter}{suffix}"
                counter += 1
        try:
            shutil.move(str(src), str(dst))
            # Restore original modification time
            if orig_mtime is not None:
                os.utime(str(dst), (orig_atime, orig_mtime))
            moved += 1
        except Exception:
            failed += 1

        if progress_callback:
            progress_callback(src.name, i + 1, total)

    # Remove empty subdirectories (deepest first)
    removed_dirs = 0
    if delete_empty:
        for d in sorted(folder.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if d.is_dir():
                try:
                    d.rmdir()  # only removes if empty
                    removed_dirs += 1
                except OSError:
                    pass

    return {"moved": moved, "skipped": skipped, "failed": failed, "removed_dirs": removed_dirs}


def fit_size(content_width, content_height, container_width, container_height):
    if content_width <= 0 or content_height <= 0:
        return container_width, container_height
    scale = min(container_width / content_width, container_height / content_height)
    return int(content_width * scale), int(content_height * scale)
