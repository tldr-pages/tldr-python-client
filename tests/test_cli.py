import io
import os
import time
import zipfile

import pytest
from conftest import write_page

from tldr import cli
from tldr.http import NetworkError, NotFound


@pytest.fixture
def env(tmp_path):
    """An environment with a fresh, offline cache in tmp_path."""
    cache = tmp_path / "cache" / "tldr"
    write_page(cache, "en", "common", "tar", "# tar\n\n> Archiver.\n\n- Create:\n\n`tar {{[-c|--create]}} {{file}}`\n")
    write_page(cache, "en", "common", "git-checkout")
    write_page(cache, "en", "linux", "apt")
    write_page(cache, "en", "windows", "dir")
    write_page(cache, "it", "common", "tar", "# tar\n\n> Archiviatore.\n")
    (cache / ".last-update").touch()
    return {
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_DATA_DIRS": str(tmp_path / "nothing"),
        "TLDR_NETWORK_ENABLED": "0",
        "TLDR_PLATFORM": "linux",
    }


def run(env, *argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    code = cli.main(list(argv), env=env, stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def test_show_page_without_tty_has_no_colors(env):
    code, out, err = run(env, "tar")
    assert code == 0
    assert out == "\n  tar\n\n  Archiver.\n\n  - Create:\n    tar --create file\n\n"
    assert "\x1b" not in out
    assert err == ""


def test_color_flag_forces_colors(env):
    assert "\x1b[" in run(env, "-c", "tar")[1]


@pytest.mark.parametrize("flags, expected", [
    ([], "tar --create file"), (["-S"], "tar -c file"), (["--long-options"], "tar --create file"),
    (["-S", "-E"], "tar [-c|--create] file"),
])
def test_option_style(env, flags, expected):
    assert expected in run(env, "tar", *flags)[1]


def test_option_style_from_env(env):
    assert "tar -c file" in run({**env, "TLDR_OPTIONS": "short"}, "tar")[1]


def test_page_name_is_joined_and_lowercased(env):
    assert run(env, "Git", "Checkout")[0] == 0


def test_not_found_exits_non_zero_with_issue_link(env):
    code, out, err = run(env, "73eb6f19cd6f")
    assert code == 1
    assert out == ""
    assert "https://github.com/tldr-pages/tldr/issues/new?title=page%20request:%2073eb6f19cd6f" in err


def test_other_platform_warning(env):
    code, out, err = run(env, "dir")
    assert code == 0 and "dir" in out
    assert "showing the `windows` page" in err


def test_explicit_platform(env):
    code, _, err = run(env, "-p", "windows", "dir")
    assert code == 0 and err == ""


def test_unknown_platform_is_an_error(env):
    code, _, err = run(env, "-p", "plan9", "tar")
    assert code == 1 and "unknown platform" in err


def test_language_from_env(env):
    assert "Archiviatore" in run({**env, "LANG": "it_IT.UTF-8"}, "tar")[1]


def test_strict_language(env):
    assert "Archiviatore" in run(env, "-L", "it", "tar")[1]
    code, _, err = run(env, "-L", "it", "apt")
    assert code == 1 and "not available in `it`" in err


def test_list_is_one_name_per_line(env):
    code, out, _ = run(env, "--list")
    assert code == 0
    assert out == "apt\ngit-checkout\ntar\n"


def test_list_for_platform(env):
    assert run(env, "-l", "-p", "windows")[1] == "dir\ngit-checkout\ntar\n"


def test_search(env):
    assert run(env, "--search", "GIT")[1] == "git-checkout\n"
    assert run(env, "--search", "zzz")[0] == 1


def test_markdown(env):
    assert run(env, "-m", "tar")[1].startswith("# tar\n\n> Archiver.")


def test_render_file(env, tmp_path):
    page = tmp_path / "foo.md"
    page.write_text("# foo\n\n> Foo.\n")
    assert run(env, "-r", str(page))[1] == "\n  foo\n\n  Foo.\n\n"
    assert run(env, "-r", str(tmp_path / "missing.md"))[0] == 1


def test_source_directory(env, pages):
    write_page(pages, "en", "common", "only-here")
    assert run(env, "-s", str(pages / "pages"), "only-here")[0] == 0
    assert run(env, "-s", str(pages), "only-here")[0] == 0
    assert run(env, "-s", str(pages), "tar")[0] == 1


def test_no_cache_and_no_network(env, tmp_path):
    code, _, err = run({**env, "XDG_CACHE_HOME": str(tmp_path / "empty")}, "tar")
    assert code == 1 and "tldr --update" in err


def test_system_pages_used_without_user_cache(env, tmp_path):
    system = tmp_path / "share" / "tldr"
    write_page(system, "en", "common", "from-system")
    env = {**env, "XDG_CACHE_HOME": str(tmp_path / "empty"), "XDG_DATA_DIRS": str(tmp_path / "share")}
    assert run(env, "from-system")[0] == 0


def test_stale_cache_refresh_failure_still_shows_page(env, tmp_path, monkeypatch):
    stamp = tmp_path / "cache" / "tldr" / ".last-update"
    old = time.time() - 365 * 24 * 3600
    os.utime(stamp, (old, old))

    def offline(self, url):
        raise NetworkError("offline")

    monkeypatch.setattr("tldr.http.Http.get", offline)
    code, out, err = run({**env, "TLDR_NETWORK_ENABLED": "1"}, "tar")
    assert code == 0 and "tar" in out
    assert "could not refresh" in err


def test_update_then_show(env, monkeypatch):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("common/fresh.md", "# fresh\n")
    requested = []

    def fake_get(self, url):
        requested.append(url)
        if url.endswith("/tldr-pages.en.zip"):
            return archive.getvalue()
        raise NotFound(url)

    monkeypatch.setattr("tldr.http.Http.get", fake_get)
    code, out, err = run({**env, "TLDR_NETWORK_ENABLED": "1"}, "-u", "fresh")
    assert code == 0 and "fresh" in out
    assert "Updated `en`: 1 pages." in err
    assert run(env, "-u")[0] == 0


def test_no_arguments_prints_help(env):
    code, _, err = run(env)
    assert code == 1 and "usage:" in err


def test_version(env, capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"], env=env)
    assert exit_info.value.code == 0
    assert "Client Specification 2.3" in capsys.readouterr().out
