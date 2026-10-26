"""Places pages can be read from.

Every store is addressed the same way as the tldr repository: a base `pages`
directory (or URL) with translations next to it in `pages.<lang>`, each
holding one directory per platform.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from tldr.http import Http, NotFound
from tldr.languages import pages_dirname


class PageStore(Protocol):
    # Whether lookups are cheap enough to probe every platform (for the
    # "also available on ..." notice) rather than stopping at the first hit.
    local: bool

    def read(self, name: str, platform: str, language: str) -> str | None: ...

    def platforms(self) -> set[str]: ...

    def names(self, platform: str, language: str) -> set[str]: ...


class DirectoryStore:
    local = True

    def __init__(self, root: Path):
        """``root`` is the directory that contains ``pages``, ``pages.it``, ..."""
        self.root = root

    def _dir(self, platform: str, language: str) -> Path:
        return self.root / pages_dirname(language) / platform

    def read(self, name: str, platform: str, language: str) -> str | None:
        try:
            return (self._dir(platform, language) / f"{name}.md").read_text(encoding="utf-8")
        except (FileNotFoundError, NotADirectoryError):
            return None

    def platforms(self) -> set[str]:
        pages = self.root / "pages"
        if not pages.is_dir():
            return set()
        return {entry.name for entry in pages.iterdir() if entry.is_dir()}

    def names(self, platform: str, language: str) -> set[str]:
        directory = self._dir(platform, language)
        if not directory.is_dir():
            return set()
        return {entry.stem for entry in directory.glob("*.md")}

    def __repr__(self) -> str:
        return f"DirectoryStore({str(self.root)!r})"


class RemoteStore:
    """Fetches single pages over HTTP. Used when the cache is disabled."""

    local = False

    def __init__(self, pages_url: str, http: Http):
        """``pages_url`` points at the English ``pages`` directory."""
        self.pages_url = pages_url.rstrip("/")
        self.http = http

    def read(self, name: str, platform: str, language: str) -> str | None:
        base = self.pages_url if language == "en" else f"{self.pages_url}.{language}"
        try:
            return self.http.get(f"{base}/{quote(platform)}/{quote(name)}.md").decode("utf-8")
        except NotFound:
            return None

    def platforms(self) -> set[str]:
        return set()

    def names(self, platform: str, language: str) -> set[str]:
        return set()

    def __repr__(self) -> str:
        return f"RemoteStore({self.pages_url!r})"
