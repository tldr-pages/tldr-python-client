from pathlib import Path

import pytest

from tldr.render import PLAIN, Theme, parse_command, render_command, render_page, sgr

DATA = Path(__file__).parent / "data"


# Every example from the "Page structure" section of the client specification.
@pytest.mark.parametrize("command, style, expected", [
    ("ping {{example.com}}", "long", "ping example.com"),
    (
        r"docker inspect --format '\{\{range.NetworkSettings.Networks\}\}\{\{.IPAddress\}\}\{\{end\}\}' {{container}}",
        "long",
        "docker inspect --format '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' container",
    ),
    (r"mount \\{{computer_name}}\{{share_name}} Z:", "long", r"mount \\computer_name\share_name Z:"),
    ("git stash show --patch {{stash@{0}}}", "long", "git stash show --patch stash@{0}"),
    ("git add {{[-A|--all]}}", "short", "git add -A"),
    ("git add {{[-A|--all]}}", "long", "git add --all"),
    ("git add {{[-A|--all]}}", "both", "git add [-A|--all]"),
])
def test_spec_examples(command, style, expected):
    assert render_command(command, style, PLAIN) == expected


@pytest.mark.parametrize("command, expected", [
    # Only a fully escaped pair is an escape; lone backslashes are shown.
    (r"echo \{ \{{x}}", r"echo \{ \x"),
    # A literal brace directly around a placeholder.
    ("jq '{{{key}}: 1}'", "jq '{key: 1}'"),
    ("jq '.{{a}}}'", "jq '.a}'"),
    # Unclosed placeholders are shown as written.
    ("echo {{oops", "echo {{oops"),
])
def test_placeholder_edge_cases(command, expected):
    assert render_command(command, "long", PLAIN) == expected


def test_parse_command_marks_placeholders():
    tokens = parse_command("cp {{src}} {{[-r|--recursive]}} {{dst}}", "both")
    assert [(t.text, t.placeholder) for t in tokens] == [
        ("cp ", False), ("src", True), (" ", False), ("[-r|--recursive]", True), (" ", False), ("dst", True),
    ]


def test_selected_option_form_is_not_highlighted():
    tokens = parse_command("git add {{[-A|--all]}}", "short")
    assert [(t.text, t.placeholder) for t in tokens] == [("git add -A", False)]


@pytest.mark.parametrize("name", ["gem", "jq"])
def test_whole_page_plain(name):
    markdown = (DATA / f"{name}.md").read_text()
    assert render_page(markdown, "both") == (DATA / f"{name}.txt").read_text()


def test_description_strips_only_autolink_brackets():
    page = "# x\n\n> Turns a -> b.\n> More information: <https://example.com>.\n"
    rendered = render_page(page)
    assert "  Turns a -> b." in rendered
    assert "  More information: https://example.com." in rendered


def test_unknown_lines_are_kept():
    assert "  Some new kind of line" in render_page("# x\n\nSome new kind of line\n")


def test_colors():
    theme = Theme({"command": "blue underline", "parameter": "nonsense"})
    assert render_command("ls {{dir}}", "long", theme) == "\x1b[34;4mls \x1b[0mdir"


def test_sgr():
    assert sgr("red on_yellow bold") == "\x1b[31;43;1m"
    assert sgr("") == ""
