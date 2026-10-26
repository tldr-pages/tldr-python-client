"""Host-platform detection and platform lookup order."""

from __future__ import annotations

import sys
from collections.abc import Iterable

COMMON = "common"

# Platforms we know about even when no pages are on disk yet (e.g. when
# reading pages straight from a URL). New platforms found in the cache are
# picked up automatically, as the spec recommends.
KNOWN = ("android", "common", "freebsd", "linux", "netbsd", "openbsd", "osx", "sunos", "windows")

ALIASES = {"macos": "osx", "darwin": "osx", "win32": "windows"}

# `sys.platform` prefix -> tldr platform. Anything unknown is treated as Linux.
_SYS_PLATFORMS = (
    ("android", "android"),
    ("linux", "linux"),
    ("darwin", "osx"),
    ("win32", "windows"),
    ("freebsd", "freebsd"),
    ("openbsd", "openbsd"),
    ("netbsd", "netbsd"),
    ("sunos", "sunos"),
)


def normalize(name: str) -> str:
    name = name.strip().lower()
    return ALIASES.get(name, name)


def host(sys_platform: str = sys.platform) -> str:
    for prefix, platform in _SYS_PLATFORMS:
        if sys_platform.startswith(prefix):
            return platform
    return "linux"


def lookup_order(first: str, available: Iterable[str]) -> list[str]:
    """``first``, then ``common``, then every other platform alphabetically."""
    order = [first]
    if COMMON not in order:
        order.append(COMMON)
    order += sorted(set(available) - set(order))
    return order
