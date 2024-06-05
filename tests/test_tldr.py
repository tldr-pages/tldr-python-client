import io
from pathlib import Path

import pytest
import sys
import tldr
import types
from unittest import mock

# gem is a basic test of page rendering
# jq is a more complicated test for token parsing
page_names = ('gem', 'jq')


@pytest.mark.parametrize("page_name", page_names)
def test_whole_page(page_name, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    with open(f"tests/data/{page_name}.md", "rb") as f_original:
        with open(f"tests/data/{page_name}_rendered", "rb") as f_rendered:
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            sys.stdout.buffer = types.SimpleNamespace()
            sys.stdout.buffer.write = lambda x: sys.stdout.write(x.decode("utf-8"))
            tldr.output(f_original)

            sys.stdout.seek(0)
            tldr_output = sys.stdout.read().encode("utf-8")
            sys.stdout = old_stdout

            correct_output = f_rendered.read()
            assert tldr_output == correct_output


@pytest.mark.parametrize("page_name", page_names)
def test_markdown_mode(page_name):
    with open(f"tests/data/{page_name}.md", "rb") as f_original:
        d_original = f_original.read()
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        sys.stdout.buffer = types.SimpleNamespace()
        sys.stdout.buffer.write = lambda x: sys.stdout.write(x.decode("utf-8"))
        tldr.output(d_original.splitlines(), plain=True)

        sys.stdout.seek(0)
        tldr_output = sys.stdout.read().encode("utf-8")
        sys.stdout = old_stdout

        # tldr adds a trailing newline
        assert tldr_output == d_original + b"\n"


def test_error_message():
    with mock.patch("sys.argv", ["tldr", "73eb6f19cd6f"]):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            tldr.main()
        correct_output = "`73eb6f19cd6f` documentation is not available.\nIf you want to contribute it, feel free to send a pull request to: https://github.com/tldr-pages/tldr" # noqa
        print("Test {}".format(pytest_wrapped_e))
        assert pytest_wrapped_e.type == SystemExit
        assert str(pytest_wrapped_e.value) == correct_output


@pytest.mark.parametrize("language,expected", [
    ("en_US.UTF-8", "en"),
    ("en_US", "en"),
    ("en", "en"),
    ("pt_BR", "pt_BR"),
    ("pt_PT", "pt_PT"),
    ("zh_TW", "zh_TW"),
    ("pt", "pt_PT")
])
def test_get_language_code(language, expected):
    assert tldr.get_language_code(language) == expected


@pytest.mark.parametrize("language,expected", [
    ("en_US.UTF-8", "en"),
    ("POSIX", None),
    ("C", None)
])
def test_get_default_language(language, expected, monkeypatch):
    monkeypatch.setenv("LANG", language)
    assert tldr.get_default_language() == expected


def test_get_default_language_unset(monkeypatch):
    monkeypatch.delenv("LANG", raising=False)
    assert tldr.get_default_language() is None


@pytest.mark.parametrize("tldr_language, language, lang, expected", [
    ("en", None, "fr_FR", ["en", "fr"]),
    ("de", "ja_JA:cz_CZ", "cz_CZ", ["de", "ja", "cz", "en"]),
    ("it", None, "C", ["it", "en"]),
])
def test_tldr_language(tldr_language, language, lang, expected, monkeypatch):
    for name, var in [("TLDR_LANGUAGE", tldr_language),
                      ("LANGUAGE", language),
                      ("LANG", lang)]:
        # Unset environment variable if their value is given as None
        if var is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, var)
    assert tldr.get_language_list() == expected


@pytest.mark.parametrize("platform, expected", [
    ("linux2", "linux"),
    ("win32", "windows"),
    ("darwin", "osx"),
    ("sunos", "sunos"),
    ("freebsd", "freebsd"),
    ("openbsd", "openbsd"),
    ("netbsd", "netbsd"),
    ("aix", "linux"),
])
def test_get_platform(platform, expected):
    with mock.patch("sys.platform", platform):
        assert tldr.get_platform() == expected


def test_get_cache_dir_xdg(monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", "/tmp/cache")
    assert tldr.get_cache_dir() == Path("/tmp/cache/tldr")


def test_get_cache_dir_home(monkeypatch):
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("HOME", "/tmp/home")
    assert tldr.get_cache_dir() == Path("/tmp/home/.cache/tldr")


def test_get_cache_dir_default(monkeypatch):
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.setattr(Path, 'home', lambda: Path('/tmp/expanduser'))
    assert tldr.get_cache_dir() == Path("/tmp/expanduser/.cache/tldr")


def test_get_commands(monkeypatch, tmp_path):
    cache_default = tmp_path / ".cache" / "tldr" / "pages" / "linux"
    Path.mkdir(cache_default, parents=True)
    Path.touch(cache_default / "lspci.md")

    monkeypatch.setenv("HOME", tmp_path)

    result = tldr.get_commands(platforms=["linux"])

    assert isinstance(result, list)
    assert "lspci (en)" in result

    cache_zh = tmp_path / ".cache" / "tldr" / "pages.zh" / "linux"
    Path.mkdir(cache_zh, parents=True)
    Path.touch(cache_zh / "lspci.md")

    result = tldr.get_commands(platforms=["linux"], language=["zh_CN"])

    assert "lspci (zh)" in result
