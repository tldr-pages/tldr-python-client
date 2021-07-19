import sys
import io
import types
from unittest import mock
import tldr
import pytest


def test_whole_page():
    with open("tests/data/gem.md", "rb") as f_original:
        with open("tests/data/gem_rendered", "rb") as f_rendered:
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


def test_error_message():
    with mock.patch("sys.argv", ["tldr", "73eb6f19cd6f"]):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            tldr.main()
        correct_output = "`73eb6f19cd6f` documentation is not available. If you want to contribute it, feel free to send a pull request to: https://github.com/tldr-pages/tldr" # noqa
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
    ("freebsd", "linux"),
    ("aix", "linux"),
])
def test_get_platform(platform, expected):
    with mock.patch("sys.platform", platform):
        assert tldr.get_platform() == expected
