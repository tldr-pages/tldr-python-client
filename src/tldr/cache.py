"""The offline page cache: downloading, refreshing and clearing it."""

from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from tldr.http import Http, NetworkError, NotFound
from tldr.languages import pages_dirname
from tldr.stores import DirectoryStore

# Archive entries look like `linux/ls.md`. Anything else (directories,
# index files, paths trying to escape the cache) is ignored.
_ENTRY = re.compile(r"^(?P<platform>[a-z0-9][a-z0-9-]*)/(?P<page>[^/\\]+\.md)$")

_STAMP = ".last-update"


@dataclass(frozen=True)
class UpdateResult:
    language: str
    pages: int = 0
    error: str | None = None  # None on success; "not found" when no archive exists


class Cache:
    def __init__(self, directory: Path, http: Http, archive_base_url: str):
        self.directory = directory
        self.http = http
        self.archive_base_url = archive_base_url
        self.store = DirectoryStore(directory)

    def exists(self) -> bool:
        return (self.directory / "pages").is_dir()

    def age_hours(self) -> float | None:
        try:
            return (time.time() - (self.directory / _STAMP).stat().st_mtime) / 3600
        except FileNotFoundError:
            return None

    def is_stale(self, max_age_hours: float) -> bool:
        age = self.age_hours()
        return age is None or age > max_age_hours

    def update(self, languages: list[str]) -> list[UpdateResult]:
        """Download one archive per language and swap it in atomically.

        Languages without an archive are reported, not treated as failures:
        locale candidates like `en_US` are expected to miss.
        """
        self.directory.mkdir(parents=True, exist_ok=True)
        results = [self._update_language(language) for language in languages]
        if any(result.error is None for result in results):
            (self.directory / _STAMP).touch()
        return results

    def _update_language(self, language: str) -> UpdateResult:
        url = f"{self.archive_base_url}/tldr-pages.{language}.zip"
        try:
            archive = ZipFile(BytesIO(self.http.get(url)))
        except NotFound:
            return UpdateResult(language, error="not found")
        except (NetworkError, BadZipFile) as error:
            return UpdateResult(language, error=str(error))

        target = self.directory / pages_dirname(language)
        staging = target.with_name(target.name + ".new")
        shutil.rmtree(staging, ignore_errors=True)

        count = 0
        with archive:
            for entry in archive.namelist():
                match = _ENTRY.match(entry)
                if not match:
                    continue
                destination = staging / match["platform"] / match["page"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(entry))
                count += 1

        if count == 0:
            shutil.rmtree(staging, ignore_errors=True)
            return UpdateResult(language, error="archive contained no pages")

        retired = target.with_name(target.name + ".old")
        shutil.rmtree(retired, ignore_errors=True)
        if target.exists():
            target.rename(retired)
        staging.rename(target)
        shutil.rmtree(retired, ignore_errors=True)
        return UpdateResult(language, pages=count)

    def clear(self) -> bool:
        if not self.directory.exists():
            return False
        shutil.rmtree(self.directory)
        return True
