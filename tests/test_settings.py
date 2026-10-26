import os
from pathlib import Path

import pytest

from tldr.settings import ARCHIVE_BASE_URL, RAW_PAGES_URL, Settings


def test_cache_dir_xdg():
    assert Settings.from_env({"XDG_CACHE_HOME": "/tmp/cache"}).cache_dir == Path("/tmp/cache/tldr")


def test_cache_dir_home():
    assert Settings.from_env({"HOME": "/tmp/home"}).cache_dir == Path("/tmp/home/.cache/tldr")


def test_cache_dir_default(monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: Path("/tmp/expanduser"))
    assert Settings.from_env({}).cache_dir == Path("/tmp/expanduser/.cache/tldr")


def test_system_dirs():
    env = {"XDG_DATA_DIRS": os.pathsep.join(["/a", "", "/b"])}
    assert Settings.from_env(env).system_dirs == (Path("/a/tldr"), Path("/b/tldr"))


@pytest.mark.parametrize("value, expected", [("0", False), ("1", True), ("false", False), ("", True), ("yes", True)])
def test_bool_values(value, expected):
    assert Settings.from_env({"TLDR_CACHE_ENABLED": value}).cache_enabled is expected


def test_bad_number_falls_back_to_default():
    assert Settings.from_env({"TLDR_CACHE_MAX_AGE": "abc"}).cache_max_age_hours == 24 * 7


def test_legacy_archive_url_is_accepted():
    env = {"TLDR_DOWNLOAD_CACHE_LOCATION": f"{ARCHIVE_BASE_URL}/tldr.zip"}
    assert Settings.from_env(env).archive_base_url == ARCHIVE_BASE_URL


def test_disabling_cache_reads_from_network():
    assert Settings.from_env({"TLDR_CACHE_ENABLED": "0"}).pages_source == RAW_PAGES_URL
    assert Settings.from_env({}).pages_source is None


def test_unknown_option_style_defaults_to_long():
    assert Settings.from_env({"TLDR_OPTIONS": "medium"}).option_style == "long"
    assert Settings.from_env({"TLDR_OPTIONS": "Short"}).option_style == "short"


def test_colors():
    assert Settings.from_env({"TLDR_COLOR_NAME": "cyan"}).colors == {"name": "cyan"}
