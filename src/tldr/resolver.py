"""Page resolution, following the "Page resolution" section of the spec.

Platform takes precedence over language: every preferred language is tried
for a platform before moving on to the next platform.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from tldr.stores import PageStore


@dataclass(frozen=True)
class Page:
    name: str
    platform: str
    language: str
    text: str


def page_name(words: Sequence[str]) -> str:
    """``["git", "Checkout"]`` -> ``"git-checkout"``."""
    return "-".join(words).lower()


class Resolver:
    def __init__(self, stores: Sequence[PageStore], platforms: Sequence[str], languages: Sequence[str]):
        self.stores = stores
        self.platforms = platforms
        self.languages = languages

    def find(self, name: str) -> Page | None:
        for platform in self.platforms:
            if page := self._find_on(name, platform):
                return page
        return None

    def other_platforms(self, name: str, found: Page) -> list[str]:
        """Platforms other than ``found.platform`` that also have this page.

        Only local stores are consulted; probing every platform over the
        network would cost a request each.
        """
        if not all(store.local for store in self.stores):
            return []
        return [
            platform
            for platform in self.platforms
            if platform != found.platform and self._find_on(name, platform)
        ]

    def names(self, platforms: Sequence[str]) -> list[str]:
        found: set[str] = set()
        for store in self.stores:
            for platform in platforms:
                for language in self.languages:
                    found |= store.names(platform, language)
        return sorted(found)

    def _find_on(self, name: str, platform: str) -> Page | None:
        for language in self.languages:
            for store in self.stores:
                text = store.read(name, platform, language)
                if text is not None:
                    return Page(name, platform, language, text)
        return None
