import io
import os
import time
import zipfile
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

import pytest

import tldr

DATA = Path(__file__).parent / "data"


def write_page(root, language, platform, name, text=None):
    directory = root / tldr.pages_dir_name(language) / platform
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.md").write_text(text or f"# {name}\n\n> {language}/{platform}\n")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    """No test sees the real environment, cache or network."""
    for name in list(os.environ):
        if name.startswith(("TLDR_", "LANG", "XDG_")) or name in ("NO_COLOR", "FORCE_COLOR"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "share"))
    monkeypatch.setenv("TLDR_NETWORK_ENABLED", "0")
    monkeypatch.setenv("TLDR_PLATFORM", "linux")


@pytest.fixture
def cache(tmp_path):
    cache = tmp_path / "cache" / "tldr"
    write_page(cache, "en", "common", "tar",
               "# tar\n\n> Archiver.\n\n- Create:\n\n`tar {{[-c|--create]}} {{file}}`\n")
    write_page(cache, "en", "common", "git-checkout")
    write_page(cache, "en", "linux", "apt")
    write_page(cache, "en", "windows", "dir")
    write_page(cache, "it", "common", "tar", "# tar\n\n> Archiviatore.\n")
    (cache / tldr.CACHE_STAMP).touch()
    return cache


def run(capsys, *argv):
    code = tldr.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


# --- Rendering ---------------------------------------------------------------

def render_command(command, style="long"):
    return "".join(text for text, _ in tldr.split_placeholders(command, style))


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
    assert render_command(command, style) == expected


@pytest.mark.parametrize("command, expected", [
    (r"echo \{ \{{x}}", r"echo \{ \x"),
    ("jq '{{{key}}: 1}'", "jq '{key: 1}'"),
    ("jq '.{{a}}}'", "jq '.a}'"),
    ("echo {{oops", "echo {{oops"),
    # Escaped braces inside a placeholder (aws-dynamodb, fakedata, x8 pages).
    (r"""--item '{{{"A": {"S": "v"\}\}}}'""", """--item '{"A": {"S": "v"}}'"""),
    (r'echo "{{\{\{Generator\}\}}}"', 'echo "{{Generator}}"'),
    # Square brackets are only an option placeholder in the `[short|long]` form.
    ("tuc --regex '{{[, ]+}}' --fields 1,3", "tuc --regex '[, ]+' --fields 1,3"),
    # The legacy client used this text as an internal sentinel and mangled it.
    ("echo __ESCAPED_OPEN__ {{x}}", "echo __ESCAPED_OPEN__ x"),
])
def test_placeholder_edge_cases(command, expected):
    assert render_command(command) == expected


def test_split_placeholders():
    assert tldr.split_placeholders("cp {{src}} {{[-r|--recursive]}} {{dst}}", "both") == [
        ("cp ", False), ("src", True), (" ", False), ("[-r|--recursive]", True), (" ", False), ("dst", True),
    ]
    # The chosen option form is plain command text, not a placeholder.
    assert tldr.split_placeholders("git add {{[-A|--all]}}", "short") == [("git add -A", False)]


@pytest.mark.parametrize("name", ["gem", "jq"])
def test_whole_page_plain(name):
    markdown = (DATA / f"{name}.md").read_text()
    assert tldr.render_page(markdown, "both") == (DATA / f"{name}.txt").read_text()


def test_description_strips_only_autolink_brackets():
    rendered = tldr.render_page("# x\n\n> Turns a -> b.\n> More information: <https://example.com>.\n")
    assert "  Turns a -> b." in rendered
    assert "  More information: https://example.com." in rendered


def test_unknown_lines_are_kept():
    assert "  Some new kind of line" in tldr.render_page("# x\n\nSome new kind of line\n")


def test_colors_from_env(monkeypatch):
    monkeypatch.setenv("TLDR_COLOR_COMMAND", "blue underline")
    monkeypatch.setenv("TLDR_COLOR_PARAMETER", "nonsense")
    assert tldr.colors_of("command") == ("blue", None, ["underline"])
    assert tldr.colors_of("parameter") == (None, None, [])
    rendered = tldr.render_page("`ls {{dir}}`", color=True)
    assert "\x1b[4m\x1b[34mls \x1b[0mdir" in rendered


# --- Languages and platforms -------------------------------------------------

@pytest.mark.parametrize("language, expected", [
    ("en_US.UTF-8", "en"), ("en_US", "en"), ("en", "en"), ("pt_BR", "pt_BR"), ("pt_PT", "pt_PT"),
    ("zh_TW", "zh_TW"), ("pt", "pt_PT"), ("de_DE@euro", "de"), ("C", None), ("POSIX", None), ("", None),
])
def test_get_language_code(language, expected):
    assert tldr.get_language_code(language) == expected


@pytest.mark.parametrize("tldr_language, language, lang, expected", [
    ("en", None, "fr_FR", ["en", "fr"]),
    ("de", "ja_JA:cz_CZ", "cz_CZ", ["de", "ja", "cz", "en"]),
    ("it", None, "C", ["it", "en"]),
    # The spec's table: LANGUAGE only counts when LANG is set.
    (None, "it:cz:de", "cz", ["it", "cz", "de", "en"]),
    (None, "it:de:fr", "cz", ["it", "de", "fr", "cz", "en"]),
    (None, "it:cz", None, ["en"]),
    (None, None, None, ["en"]),
])
def test_get_language_list(tldr_language, language, lang, expected, monkeypatch):
    for name, value in [("TLDR_LANGUAGE", tldr_language), ("LANGUAGE", language), ("LANG", lang)]:
        if value is not None:
            monkeypatch.setenv(name, value)
    assert tldr.get_language_list() == expected


@pytest.mark.parametrize("platform, expected", [
    ("linux2", "linux"), ("win32", "windows"), ("darwin", "osx"), ("sunos", "sunos"),
    ("freebsd", "freebsd"), ("openbsd", "openbsd"), ("netbsd", "netbsd"), ("aix", "linux"),
])
def test_get_platform(platform, expected):
    with mock.patch("sys.platform", platform):
        assert tldr.get_platform() == expected


def test_platform_list_discovers_new_platforms(tmp_path):
    write_page(tmp_path, "en", "dos", "dir")
    all_platforms = tldr.get_all_platforms([tmp_path])
    assert "dos" in all_platforms
    order = tldr.get_platform_list("windows", all_platforms)
    assert order[:2] == ["windows", "common"]
    assert sorted(order) == all_platforms


def test_get_cache_dir(monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", "/tmp/cache")
    assert tldr.get_cache_dir() == Path("/tmp/cache/tldr")
    monkeypatch.delenv("XDG_CACHE_HOME")
    monkeypatch.setenv("HOME", "/tmp/home")
    assert tldr.get_cache_dir() == Path("/tmp/home/.cache/tldr")


# --- Lookup ------------------------------------------------------------------

def test_platform_beats_language(tmp_path):
    write_page(tmp_path, "it", "common", "ls", "it/common")
    write_page(tmp_path, "en", "linux", "ls", "en/linux")
    assert tldr.find_page("ls", [tmp_path], ["linux", "common"], ["it", "en"]) == ("en/linux", "linux")


def test_system_pages_on_host_platform_beat_user_cache_on_other_platform(tmp_path):
    # Regression for the legacy XDG_DATA_DIRS lookup (#329), which searched the whole
    # user cache first and so preferred user-cache `osx` over system `linux`.
    user, system = tmp_path / "user", tmp_path / "system"
    write_page(user, "en", "osx", "ls", "user/osx")
    write_page(system, "en", "linux", "ls", "system/linux")
    assert tldr.find_page("ls", [user, system], ["linux", "common", "osx"], ["en"]) == ("system/linux", "linux")


def test_every_xdg_data_dir_is_used(monkeypatch, tmp_path):
    for name in ("a", "b"):
        write_page(tmp_path / name / "tldr", "en", "common", f"from-{name}")
    monkeypatch.setenv("XDG_DATA_DIRS", f"{tmp_path / 'a'}:{tmp_path / 'b'}")
    assert tldr.get_local_sources() == [tmp_path / "a" / "tldr", tmp_path / "b" / "tldr"]


def test_remote_source(monkeypatch):
    requested = []

    def fake_download(url):
        requested.append(url)
        if url == "https://example.com/pages.it/common/tar.md":
            return b"# tar"
        raise HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(tldr, "download", fake_download)
    assert tldr.find_page("tar", ["https://example.com/pages"], ["linux", "common"], ["it", "en"]) == (
        "# tar", "common")
    assert requested[0] == "https://example.com/pages.it/linux/tar.md"


# --- Cache -------------------------------------------------------------------

def make_archive(pages):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in pages.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def test_update_cache(monkeypatch, tmp_path, capsys):
    cache = tmp_path / "cache" / "tldr"
    write_page(cache, "en", "common", "deleted-upstream")
    archives = {
        "https://example.com/tldr-pages.en.zip": make_archive({
            "common/tar.md": "# tar", "linux/apt.md": "# apt", "LICENSE.md": "x", "../evil.md": "x",
        }),
    }

    def fake_download(url):
        if url not in archives:
            raise HTTPError(url, 404, "Not Found", None, None)
        return archives[url]

    monkeypatch.setattr(tldr, "download", fake_download)
    monkeypatch.setenv("TLDR_DOWNLOAD_CACHE_LOCATION", "https://example.com/tldr.zip")

    assert tldr.update_cache(["eo", "en"])
    assert (cache / "pages" / "common" / "tar.md").read_text() == "# tar"
    assert (cache / "pages" / "linux" / "apt.md").exists()
    assert not (cache / "pages" / "common" / "deleted-upstream.md").exists()
    assert not (tmp_path / "cache" / "evil.md").exists()
    assert (cache / tldr.CACHE_STAMP).exists()
    assert sorted(path.name for path in cache.iterdir()) == [tldr.CACHE_STAMP, "pages"]
    assert "en: 2 entries" in capsys.readouterr().err


def test_first_run_downloads_cache(monkeypatch, capsys):
    monkeypatch.setenv("TLDR_NETWORK_ENABLED", "1")
    monkeypatch.setattr(tldr, "download", lambda url: make_archive({"common/tar.md": "# tar\n"}))
    code, out, err = run(capsys, "tar")
    assert code == 0 and "tar" in out
    assert "Downloading tldr pages" in err


def test_new_language_triggers_download_once(monkeypatch, capsys):
    requested = []

    def fake_download(url):
        requested.append(url)
        if url.endswith(".eo.zip"):
            raise HTTPError(url, 404, "Not Found", None, None)
        return make_archive({"common/tar.md": "# tar\n"})

    monkeypatch.setenv("TLDR_NETWORK_ENABLED", "1")
    monkeypatch.setattr(tldr, "download", fake_download)
    run(capsys, "tar")
    assert len(requested) == 1
    monkeypatch.setenv("LANG", "it_IT.UTF-8")
    monkeypatch.setenv("LANGUAGE", "eo")
    run(capsys, "tar")
    assert [url.rsplit("/", 1)[1] for url in requested[1:]] == [
        "tldr-pages.eo.zip", "tldr-pages.it.zip", "tldr-pages.en.zip"]
    run(capsys, "tar")
    assert len(requested) == 4  # `eo` has no archive, but it isn't retried on every run


def test_stale_cache_refresh_failure_still_shows_page(cache, monkeypatch, capsys):
    old = time.time() - 365 * 24 * 3600
    os.utime(cache / tldr.CACHE_STAMP, (old, old))

    def offline(url):
        raise URLError("offline")

    monkeypatch.setenv("TLDR_NETWORK_ENABLED", "1")
    monkeypatch.setattr(tldr, "download", offline)
    code, out, err = run(capsys, "tar")
    assert code == 0 and "tar" in out
    assert "Could not refresh" in err


def test_cache_disabled_falls_back_to_cache_when_offline(cache, monkeypatch, capsys):
    def offline(url):
        raise URLError("offline")

    monkeypatch.setenv("TLDR_CACHE_ENABLED", "0")
    monkeypatch.setattr(tldr, "download", offline)
    code, out, err = run(capsys, "tar")
    assert code == 0 and "Archiver" in out
    assert "using the cache instead" in err


def test_clear_cache(cache, capsys):
    assert run(capsys, "--clear-cache")[0] == 0
    assert not cache.exists()


# --- Command line ------------------------------------------------------------

def test_show_page_without_tty_has_no_colors(cache, capsys):
    code, out, err = run(capsys, "tar")
    assert code == 0
    assert out == "\n  tar\n\n  Archiver.\n\n  - Create:\n    tar --create file\n\n"
    assert err == ""


def test_color_flag_forces_colors(cache, capsys):
    assert "\x1b[" in run(capsys, "-c", "tar")[1]


@pytest.mark.parametrize("flags, expected", [
    ([], "tar --create file"), (["-S"], "tar -c file"), (["--long-options"], "tar --create file"),
    (["-S", "-E"], "tar [-c|--create] file"),
])
def test_option_style(cache, capsys, flags, expected):
    assert expected in run(capsys, "tar", *flags)[1]


def test_option_style_from_env(cache, capsys, monkeypatch):
    monkeypatch.setenv("TLDR_OPTIONS", "short")
    assert "tar -c file" in run(capsys, "tar")[1]


def test_page_name_is_joined_and_lowercased(cache, capsys):
    assert run(capsys, "Git", "Checkout")[0] == 0


def test_not_found(cache, capsys):
    code, out, err = run(capsys, "73eb6f19cd6f")
    assert code == 1 and out == ""
    assert "`73eb6f19cd6f` documentation is not available." in err
    assert "https://github.com/tldr-pages/tldr/issues/new?title=page%20request:%2073eb6f19cd6f" in err


def test_other_platform_warning(cache, capsys):
    code, out, err = run(capsys, "dir")
    assert code == 0 and "dir" in out
    assert "showing page from platform 'windows'" in err


def test_also_available_notice(cache, capsys):
    write_page(cache, "en", "osx", "apt")
    assert "Also available on: osx." in run(capsys, "apt")[2]


def test_explicit_platform(cache, capsys):
    code, _, err = run(capsys, "-p", "windows", "dir")
    assert code == 0 and err == ""
    assert run(capsys, "-p", "macos", "tar")[0] == 0


def test_unknown_platform(cache, capsys, monkeypatch):
    code, _, err = run(capsys, "-p", "plan9", "tar")
    assert code == 1 and "Unknown platform" in err
    monkeypatch.setenv("TLDR_PLATFORM", "plan9")
    code, _, err = run(capsys, "tar")
    assert code == 0 and "Falling back to auto-detection" in err


def test_language_from_env(cache, capsys, monkeypatch):
    monkeypatch.setenv("LANG", "it_IT.UTF-8")
    assert "Archiviatore" in run(capsys, "tar")[1]


def test_strict_language(cache, capsys):
    assert "Archiviatore" in run(capsys, "-L", "it", "tar")[1]
    code, _, err = run(capsys, "-L", "it", "apt")
    assert code == 1 and "not available in language `it`" in err


def test_list(cache, capsys):
    assert run(capsys, "--list") == (0, "apt\ngit-checkout\ntar\n", "")
    assert run(capsys, "-l", "-p", "windows")[1] == "dir\ngit-checkout\ntar\n"


def test_search(cache, capsys):
    assert run(capsys, "--search", "GIT")[1] == "git-checkout\n"
    assert run(capsys, "--search", "zzz")[0] == 1


def test_markdown(cache, capsys):
    assert run(capsys, "-m", "tar")[1].startswith("# tar\n\n> Archiver.")


def test_render_file(capsys, tmp_path):
    page = tmp_path / "foo.md"
    page.write_text("# foo\n\n> Foo.\n")
    assert run(capsys, "-r", str(page))[1] == "\n  foo\n\n  Foo.\n\n"
    assert run(capsys, "-r", str(tmp_path / "missing.md"))[0] == 1


def test_source_directory(cache, capsys, tmp_path):
    repo = tmp_path / "repo"
    write_page(repo, "en", "common", "only-here")
    assert run(capsys, "-s", str(repo / "pages"), "only-here")[0] == 0
    assert run(capsys, "-s", str(repo), "only-here")[0] == 0
    assert run(capsys, "-s", f"file://{repo / 'pages'}", "only-here")[0] == 0
    assert run(capsys, "-s", str(repo), "tar")[0] == 1
    assert "not a tldr pages directory" in run(capsys, "-s", str(tmp_path / "nope"), "tar")[2]


def test_no_pages_and_no_network(capsys):
    code, _, err = run(capsys, "tar")
    assert code == 1 and "tldr --update" in err


def test_system_pages_without_user_cache(capsys, tmp_path):
    write_page(tmp_path / "share" / "tldr", "en", "common", "from-system")
    assert run(capsys, "from-system")[0] == 0


def test_no_arguments_prints_help(capsys):
    code, _, err = run(capsys)
    assert code == 1 and "usage:" in err


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        tldr.main(["--version"])
    assert exit_info.value.code == 0
    assert "Client Specification 2.3" in capsys.readouterr().out
