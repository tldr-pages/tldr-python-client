import pytest
from conftest import FakeHttp, write_page

from tldr import platforms
from tldr.resolver import Resolver, page_name
from tldr.stores import DirectoryStore, RemoteStore


@pytest.mark.parametrize("words, expected", [
    (["7za"], "7za"),
    (["eyeD3"], "eyed3"),
    (["git", "checkout"], "git-checkout"),
])
def test_page_name(words, expected):
    assert page_name(words) == expected


def test_platform_takes_precedence_over_language(pages):
    # The lookup table from the spec: linux, LANGUAGE="it:fr:en".
    write_page(pages, "en", "common", "some-page")
    write_page(pages, "it", "osx", "some-page")
    resolver = Resolver([DirectoryStore(pages)], ["linux", "common", "osx"], ["it", "fr", "en"])
    page = resolver.find("some-page")
    assert (page.platform, page.language) == ("common", "en")


def test_preferred_language_wins_on_same_platform(pages):
    write_page(pages, "en", "common", "ls")
    write_page(pages, "it", "common", "ls")
    page = Resolver([DirectoryStore(pages)], ["linux", "common"], ["it", "en"]).find("ls")
    assert page.language == "it"


def test_falls_back_to_other_platforms(pages):
    write_page(pages, "en", "linux", "apt")
    write_page(pages, "en", "sunos", "apt")
    resolver = Resolver([DirectoryStore(pages)], ["windows", "common", "linux", "osx", "sunos"], ["en"])
    page = resolver.find("apt")
    assert page.platform == "linux"
    assert resolver.other_platforms("apt", page) == ["sunos"]


def test_not_found(pages):
    write_page(pages, "en", "common", "ls")
    assert Resolver([DirectoryStore(pages)], ["linux", "common"], ["en"]).find("nope") is None


def test_earlier_store_wins(tmp_path):
    user, system = tmp_path / "user", tmp_path / "system"
    write_page(user, "en", "common", "ls", "# user\n")
    write_page(system, "en", "common", "ls", "# system\n")
    page = Resolver([DirectoryStore(user), DirectoryStore(system)], ["common"], ["en"]).find("ls")
    assert page.text == "# user\n"


def test_names(pages):
    write_page(pages, "en", "linux", "lspci")
    write_page(pages, "zh", "linux", "lspci")
    write_page(pages, "zh", "common", "ls")
    write_page(pages, "en", "osx", "brew")
    resolver = Resolver([DirectoryStore(pages)], ["linux", "common", "osx"], ["zh", "en"])
    assert resolver.names(["linux", "common"]) == ["ls", "lspci"]


def test_remote_store_urls():
    http = FakeHttp({"https://x/pages.it/common/git-add.md": b"# git add\n"})
    store = RemoteStore("https://x/pages/", http)
    assert store.read("git-add", "common", "it") == "# git add\n"
    assert store.read("git-add", "linux", "en") is None
    assert http.requested[-1] == "https://x/pages/linux/git-add.md"


def test_remote_store_skips_platform_probe():
    resolver = Resolver([RemoteStore("https://x/pages", FakeHttp())], ["linux", "common"], ["en"])
    assert resolver.other_platforms("ls", object()) == []


@pytest.mark.parametrize("sys_platform, expected", [
    ("linux", "linux"), ("win32", "windows"), ("darwin", "osx"), ("sunos5", "sunos"),
    ("freebsd14", "freebsd"), ("openbsd7", "openbsd"), ("netbsd10", "netbsd"),
    ("android", "android"), ("aix", "linux"),
])
def test_host_platform(sys_platform, expected):
    assert platforms.host(sys_platform) == expected


def test_lookup_order():
    assert platforms.lookup_order("windows", ["linux", "common", "dos", "windows"]) == [
        "windows", "common", "dos", "linux",
    ]
    assert platforms.lookup_order("common", ["linux", "osx"]) == ["common", "linux", "osx"]


def test_macos_alias():
    assert platforms.normalize("macOS") == "osx"
