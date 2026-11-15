"""Locale resource files (locales/<code>.json) with admin overrides layered on top."""

import json
from pathlib import Path


class Texts:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.files: dict[str, dict[str, str]] = {}
        self.overrides: dict[str, dict[str, str]] = {}
        self._mtimes: dict = {}
        self.refresh()

    def refresh(self) -> None:
        """Re-read resource files that changed on disk, so edits apply without a restart."""
        paths = sorted(self.directory.glob("*.json"))
        mtimes = {p.stem: p.stat().st_mtime for p in paths}
        if mtimes == self._mtimes:
            return
        files = {}
        for p in paths:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
                raise ValueError(f"Locale file {p} must map text keys to strings")
            files[p.stem] = data
        if "en" not in files:
            raise ValueError(f"No en.json resource file in {self.directory}")
        self.files, self._mtimes = files, mtimes

    def bundle(self, locale: str) -> dict[str, str]:
        self.refresh()
        return {
            **self.files["en"],
            **self.overrides.get("en", {}),
            **self.files.get(locale, {}),
            **self.overrides.get(locale, {}),
        }
