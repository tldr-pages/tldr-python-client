from importlib.metadata import version
import io
import os
from pathlib import Path

import pytest
import re
import subprocess
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
            tldr.output(f_original, "both")

            sys.stdout.seek(0)
            tldr_output = sys.stdout.read().encode("utf-8")
            sys.stdout = old_stdout

            correct_output = f_rendered.read()
            assert tldr_output == correct_output


@pytest.mark.parametrize("page_name", page_names)
@pytest.mark.parametrize("force_color", [True, False])
def test_whole_page_piped(page_name, force_color):
    termcolor_version = tuple(int(x) for x in version("termcolor").split(".")[:2])
    if not force_color and termcolor_version < (2, 1):
        pytest.skip("termcolor < 2.1 does not disable colors when not on a tty")
    # Run in a subprocess so that stdout is a real pipe instead of a terminal
    env = {key: value for key, value in os.environ.items()
           if key not in ("FORCE_COLOR", "NO_COLOR", "ANSI_COLORS_DISABLED")}
    if force_color:
        env["FORCE_COLOR"] = "1"
    # Text printed before the page (e.g. a warning) must stay in front of it
    code = (
        "import tldr\n"
        "print('before')\n"
        f"with open('tests/data/{page_name}.md', 'rb') as f_original:\n"
        "    tldr.output(f_original, 'both')\n"
    )
    result = subprocess.run([sys.executable, "-c", code], env=env,
                            stdout=subprocess.PIPE, check=True)

    with open(f"tests/data/{page_name}_rendered", "rb") as f_rendered:
        correct_output = f_rendered.read()
    if not force_color:
        # Without colors, no styling at all should be left
        correct_output = re.sub(rb"\x1b\[[0-9;]*m", b"", correct_output)
    assert result.stdout == b"before\n" + correct_output


@pytest.mark.parametrize("page_name", page_names)
def test_markdown_mode(page_name):
    with open(f"tests/data/{page_name}.md", "rb") as f_original:
        d_original = f_original.read()
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        sys.stdout.buffer = types.SimpleNamespace()
        sys.stdout.buffer.write = lambda x: sys.stdout.write(x.decode("utf-8"))
        tldr.output(d_original.splitlines(), "both", plain=True)

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

    monkeypatch.setenv("HOME", str(tmp_path))

    result = tldr.get_commands(platforms=["linux"])

    assert isinstance(result, list)
    assert "lspci" in result

    cache_zh = tmp_path / ".cache" / "tldr" / "pages.zh" / "linux"
    Path.mkdir(cache_zh, parents=True)
    Path.touch(cache_zh / "lspci.md")

    result = tldr.get_commands(platforms=["linux"], language=["zh_CN"])

    assert "lspci" in result
