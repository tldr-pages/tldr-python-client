"""Preferred-language detection, following the "Language" section of the spec."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

# Bare language codes that have no `pages.<code>` directory of their own.
ALIASES = {"pt": "pt_PT"}


def normalize(locale: str) -> str | None:
    """Turn a POSIX locale such as ``it_IT.UTF-8@euro`` into ``it_IT``.

    Returns None for empty values and for ``C``/``POSIX``, which the spec
    says must be ignored.
    """
    locale = locale.split(".", 1)[0].split("@", 1)[0].strip()
    if locale in ("", "C", "POSIX"):
        return None
    return locale


def candidates(locale: str) -> list[str]:
    """Page-directory language codes to try for one locale, most specific first.

    ``zh_TW`` -> ``["zh_TW", "zh"]``, ``pt`` -> ``["pt_PT"]``.
    """
    language, _, country = locale.partition("_")
    if country:
        return [f"{language}_{country}", language]
    return [ALIASES.get(language, language)]


def expand(locales: Iterable[str]) -> list[str]:
    codes: list[str] = []
    for locale in locales:
        for code in candidates(locale):
            if code not in codes:
                codes.append(code)
    return codes


def from_environment(env: Mapping[str, str], configured: str | None = None) -> list[str]:
    """Languages to try, in order. Always ends with English.

    ``configured`` (``TLDR_LANGUAGE``) is a client-specific preference that
    goes first. The rest is the spec algorithm: ``LANGUAGE`` is only honoured
    when ``LANG`` is set, and ``LANG`` comes after it.
    """
    locales: list[str] = []
    if configured and (preferred := normalize(configured)):
        locales.append(preferred)

    lang = normalize(env.get("LANG", ""))
    if lang:
        locales += [loc for loc in map(normalize, env.get("LANGUAGE", "").split(":")) if loc]
        locales.append(lang)

    locales.append("en")
    return expand(locales)


def strict(language: str) -> list[str]:
    """Languages to try when the user passed ``--language``: no English fallback."""
    locale = normalize(language)
    return expand([locale]) if locale else ["en"]


def pages_dirname(code: str) -> str:
    return "pages" if code == "en" else f"pages.{code}"
