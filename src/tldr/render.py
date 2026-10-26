"""Turning a page's Markdown into terminal output.

Example commands are parsed by a small scanner rather than regexes so that
the placeholder rules from the spec (escaping, nested braces, short/long
option placeholders) are each handled in exactly one place.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

INDENT = "  "

# Role -> default style. Values use the same vocabulary as TLDR_COLOR_*.
DEFAULT_STYLES = {
    "name": "bold",
    "description": "",
    "example": "green",
    "command": "red",
    "parameter": "",
    "code": "yellow italic",  # inline code in example descriptions
}

_COLORS = {"grey": 90, "red": 31, "green": 32, "yellow": 33, "blue": 34, "magenta": 35, "cyan": 36, "white": 37}
_ATTRIBUTES = {"bold": 1, "dark": 2, "italic": 3, "underline": 4, "blink": 5, "reverse": 7, "concealed": 8}
_RESET = "\x1b[0m"


def sgr(spec: str) -> str:
    """``"red on_yellow underline"`` -> the matching ANSI escape sequence.

    Unknown words are ignored, so a typo degrades to no styling.
    """
    codes = []
    for word in spec.split():
        if word in _COLORS:
            codes.append(_COLORS[word])
        elif word.startswith("on_") and word[3:] in _COLORS:
            codes.append(_COLORS[word[3:]] + 10)
        elif word in _ATTRIBUTES:
            codes.append(_ATTRIBUTES[word])
    return f"\x1b[{';'.join(map(str, codes))}m" if codes else ""


class Theme:
    def __init__(self, overrides: Mapping[str, str] | None = None, color: bool = True):
        styles = {**DEFAULT_STYLES, **(overrides or {})}
        self.codes = {role: sgr(spec) if color else "" for role, spec in styles.items()}

    def __call__(self, role: str, text: str) -> str:
        code = self.codes.get(role, "")
        return f"{code}{text}{_RESET}" if code and text else text


PLAIN = Theme(color=False)


# --- Example commands -------------------------------------------------------

@dataclass(frozen=True)
class Token:
    text: str
    placeholder: bool = False


_OPTION = re.compile(r"^\[(?P<short>[^|\]]+)\|(?P<long>[^\]]+)\]$")


def parse_command(command: str, option_style: str = "long") -> list[Token]:
    """Split an example command into literal text and placeholders.

    - ``{{x}}`` is a placeholder; braces inside it are kept (``{{stash@{0}}}``).
    - ``\\{\\{`` and ``\\}\\}`` are literal double braces.
    - ``{{[-A|--all]}}`` is an option placeholder: with ``short`` or ``long``
      it becomes plain command text, with ``both`` it stays a placeholder.
    """
    tokens: list[Token] = []
    text: list[str] = []

    def flush() -> None:
        if text:
            tokens.append(Token("".join(text)))
            text.clear()

    i = 0
    while i < len(command):
        if command.startswith("\\{\\{", i):
            text.append("{{")
            i += 4
        elif command.startswith("\\}\\}", i):
            text.append("}}")
            i += 4
        elif command.startswith("{{{", i):
            # A literal brace right before a placeholder: `{{{x}}` is `{` + `{{x}}`.
            text.append("{")
            i += 1
        elif command.startswith("{{", i) and (end := _placeholder_end(command, i + 2)) is not None:
            content = command[i + 2:end]
            option = _OPTION.match(content)
            if option and option_style in ("short", "long"):
                text.append(option[option_style])
            else:
                flush()
                tokens.append(Token(content, placeholder=True))
            i = end + 2
        else:
            text.append(command[i])
            i += 1
    flush()
    return tokens


def _placeholder_end(command: str, start: int) -> int | None:
    """Index of the ``}}`` closing a placeholder whose content begins at ``start``.

    Single braces inside the placeholder must balance, so in
    ``{{stash@{0}}}`` the placeholder ends at the last two braces.
    """
    depth = 0
    for i in range(start, len(command)):
        char = command[i]
        if char == "{":
            depth += 1
        elif char == "}":
            if depth == 0 and command.startswith("}}", i):
                return i
            depth = max(depth - 1, 0)
    # Unbalanced inner braces: fall back to the first closing pair.
    end = command.find("}}", start)
    return end if end != -1 else None


def render_command(command: str, option_style: str, theme: Theme) -> str:
    return "".join(
        theme("parameter" if token.placeholder else "command", token.text)
        for token in parse_command(command, option_style)
    )


# --- Whole pages ------------------------------------------------------------

_INLINE_CODE = re.compile(r"`([^`]+)`")
_AUTOLINK = re.compile(r"<([a-z][a-z0-9+.-]*:[^<>\s]+)>", re.IGNORECASE)


def _render_example_description(line: str, theme: Theme) -> str:
    parts = _INLINE_CODE.split(line)
    # re.split with one group alternates: text, code, text, code, ...
    return "".join(
        theme("code", part) if index % 2 else theme("example", part)
        for index, part in enumerate(parts)
        if part
    )


def render_page(markdown: str, option_style: str = "long", theme: Theme = PLAIN) -> str:
    lines = [""]
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            lines += [INDENT + theme("name", line[2:].strip()), ""]
        elif line.startswith(">"):
            description = _AUTOLINK.sub(r"\1", line[1:].strip())
            lines.append(INDENT + theme("description", description))
        elif line.startswith("- "):
            lines += ["", INDENT + _render_example_description(line, theme)]
        elif len(line) > 1 and line.startswith("`") and line.endswith("`"):
            lines.append(INDENT * 2 + render_command(line[1:-1], option_style, theme))
        else:
            # Anything else valid in CommonMark: show it rather than drop it.
            lines.append(INDENT + line)
    lines.append("")
    return "\n".join(lines) + "\n"
