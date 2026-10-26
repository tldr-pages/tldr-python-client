import pytest

from tldr import languages


# The table from the "Language" section of the specification.
@pytest.mark.parametrize("lang, language, expected", [
    ("cz", "it:cz:de", ["it", "cz", "de", "en"]),
    ("cz", "it:de:fr", ["it", "de", "fr", "cz", "en"]),
    ("it", None, ["it", "en"]),
    (None, "it:cz", ["en"]),
    (None, None, ["en"]),
])
def test_spec_table(lang, language, expected):
    env = {key: value for key, value in (("LANG", lang), ("LANGUAGE", language)) if value is not None}
    assert languages.from_environment(env) == expected


@pytest.mark.parametrize("env, configured, expected", [
    ({"LANG": "C"}, "it", ["it", "en"]),
    ({"LANG": "POSIX", "LANGUAGE": "de"}, None, ["en"]),
    ({"LANG": "fr_FR.UTF-8"}, "en", ["en", "fr_FR", "fr"]),
    ({"LANG": "cs_CZ", "LANGUAGE": "ja_JP:cs_CZ"}, "de", ["de", "ja_JP", "ja", "cs_CZ", "cs", "en"]),
    ({"LANG": "zh_TW.UTF-8"}, None, ["zh_TW", "zh", "en"]),
    ({"LANG": "pt"}, None, ["pt_PT", "en"]),
    ({"LANG": "pt_BR"}, None, ["pt_BR", "pt", "en"]),
])
def test_environment(env, configured, expected):
    assert languages.from_environment(env, configured) == expected


def test_strict_has_no_english_fallback():
    assert languages.strict("it_IT.UTF-8") == ["it_IT", "it"]


@pytest.mark.parametrize("value", ["", "C", "POSIX", "C.UTF-8"])
def test_ignored_locales(value):
    assert languages.normalize(value) is None


def test_pages_dirname():
    assert languages.pages_dirname("en") == "pages"
    assert languages.pages_dirname("pt_BR") == "pages.pt_BR"
