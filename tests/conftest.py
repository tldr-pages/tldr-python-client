from pathlib import Path

import pytest

from tldr.http import NotFound


def write_page(root: Path, language: str, platform: str, name: str, text: str | None = None) -> None:
    pages = root / ("pages" if language == "en" else f"pages.{language}") / platform
    pages.mkdir(parents=True, exist_ok=True)
    (pages / f"{name}.md").write_text(text or f"# {name}\n\n> {language}/{platform}\n")


class FakeHttp:
    """Serves canned responses by URL and records what was requested."""

    def __init__(self, responses: dict[str, bytes] | None = None):
        self.responses = responses or {}
        self.requested: list[str] = []

    def get(self, url: str) -> bytes:
        self.requested.append(url)
        if url not in self.responses:
            raise NotFound(url)
        return self.responses[url]


@pytest.fixture
def pages(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    return root
