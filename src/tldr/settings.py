"""Configuration read from environment variables.

Everything the client can be configured with lives in one immutable object
that is built once at startup, so nothing reads ``os.environ`` at import time
and tests can pass in any mapping they like.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

ARCHIVE_BASE_URL = "https://github.com/tldr-pages/tldr/releases/latest/download"
RAW_PAGES_URL = "https://raw.githubusercontent.com/tldr-pages/tldr/main/pages"

OPTION_STYLES = ("short", "long", "both")


@dataclass(frozen=True)
class Settings:
    cache_dir: Path
    system_dirs: tuple[Path, ...]
    cache_enabled: bool = True
    network_enabled: bool = True
    cache_max_age_hours: float = 24 * 7
    archive_base_url: str = ARCHIVE_BASE_URL
    # Where to read pages from instead of the cache: a local `pages` directory
    # or a URL pointing at one. Translations live next to it as `pages.<lang>`.
    pages_source: str | None = None
    language: str | None = None
    platform: str | None = None
    option_style: str = "long"
    allow_insecure: bool = False
    cafile: Path | None = None
    colors: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> Settings:
        cache_enabled = _bool(env, "TLDR_CACHE_ENABLED", True)
        pages_source = env.get("TLDR_PAGES_SOURCE_LOCATION") or None
        if not cache_enabled and pages_source is None:
            pages_source = RAW_PAGES_URL

        archive_url = env.get("TLDR_DOWNLOAD_CACHE_LOCATION", ARCHIVE_BASE_URL)
        # The old client took the URL of `tldr.zip`; accept that for compatibility.
        if archive_url.endswith(".zip"):
            archive_url = archive_url.rsplit("/", 1)[0]

        option_style = env.get("TLDR_OPTIONS", "long").strip().lower()
        if option_style not in OPTION_STYLES:
            option_style = "long"

        cafile = env.get("TLDR_CERT")

        return cls(
            cache_dir=_user_cache_dir(env),
            system_dirs=_system_dirs(env),
            cache_enabled=cache_enabled,
            network_enabled=_bool(env, "TLDR_NETWORK_ENABLED", True),
            cache_max_age_hours=_float(env, "TLDR_CACHE_MAX_AGE", 24 * 7),
            archive_base_url=archive_url.rstrip("/"),
            pages_source=pages_source.rstrip("/") if pages_source else None,
            language=env.get("TLDR_LANGUAGE") or None,
            platform=env.get("TLDR_PLATFORM", "").strip().lower() or None,
            option_style=option_style,
            allow_insecure=_bool(env, "TLDR_ALLOW_INSECURE", False),
            cafile=Path(cafile).expanduser() if cafile else None,
            colors={
                key[len("TLDR_COLOR_"):].lower(): value
                for key, value in env.items()
                if key.startswith("TLDR_COLOR_")
            },
        )


def _user_cache_dir(env: Mapping[str, str]) -> Path:
    if env.get("XDG_CACHE_HOME"):
        return Path(env["XDG_CACHE_HOME"]) / "tldr"
    if env.get("HOME"):
        return Path(env["HOME"]) / ".cache" / "tldr"
    return Path.home() / ".cache" / "tldr"


def _system_dirs(env: Mapping[str, str]) -> tuple[Path, ...]:
    """Read-only page directories installed by distribution packages."""
    data_dirs = env.get("XDG_DATA_DIRS") or os.pathsep.join(["/usr/local/share", "/usr/share"])
    return tuple(Path(entry) / "tldr" for entry in data_dirs.split(os.pathsep) if entry)


def _bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    value = env.get(key, "").strip().lower()
    if not value:
        return default
    return value not in ("0", "false", "no", "off")


def _float(env: Mapping[str, str], key: str, default: float) -> float:
    try:
        return float(env[key])
    except (KeyError, ValueError):
        return default
