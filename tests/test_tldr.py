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
        correct_output = "`73eb6f19cd6f` documentation is not available. Consider contributing Pull Request to https://github.com/tldr-pages/tldr"  # noqa
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
