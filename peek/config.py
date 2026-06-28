import json
import sys
from pathlib import Path


def _get_config_dir():
    if sys.platform == "darwin":
        config_dir = Path.home() / "Library" / "Application Support" / "PeekViewer"
    elif sys.platform == "win32":
        config_dir = Path.home() / "AppData" / "Local" / "PeekViewer"
    else:
        config_dir = Path.home() / ".config" / "peek-viewer"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


CONFIG_DIR = _get_config_dir()
CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULTS = {
    "recent_folders": [],
    "max_recent": 10,
    "slideshow_interval": 5,
    "slideshow_order": "sequential",
    "boss_key": "Ctrl+`",
    "window_positions": {},
    "volume": 100,
    "grid_max_columns": 4,
}


class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                self._data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError:
            pass

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def add_recent_folder(self, folder_path):
        folder_str = str(folder_path)
        recents = self._data.get("recent_folders", [])
        if folder_str in recents:
            recents.remove(folder_str)
        recents.insert(0, folder_str)
        max_recent = self._data.get("max_recent", 10)
        self._data["recent_folders"] = recents[:max_recent]
        self.save()

    def clear_recents(self):
        self._data["recent_folders"] = []
        self.save()


config = Config()
