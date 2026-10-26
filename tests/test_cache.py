import io
import zipfile

from conftest import FakeHttp

from tldr.cache import Cache

BASE = "https://example.com/download"


def make_zip(entries: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_update_extracts_pages(tmp_path):
    http = FakeHttp({
        f"{BASE}/tldr-pages.en.zip": make_zip({"common/ls.md": "# ls\n", "linux/apt.md": "# apt\n", "index.json": "{}"}),
        f"{BASE}/tldr-pages.it.zip": make_zip({"common/ls.md": "# ls (it)\n"}),
    })
    cache = Cache(tmp_path / "tldr", http, BASE)
    results = cache.update(["it", "it_IT", "en"])

    assert [(r.language, r.pages, r.error) for r in results] == [
        ("it", 1, None), ("it_IT", 0, "not found"), ("en", 2, None),
    ]
    assert cache.store.read("ls", "common", "it") == "# ls (it)\n"
    assert cache.store.read("apt", "linux", "en") == "# apt\n"
    assert cache.store.platforms() == {"common", "linux"}
    assert not cache.is_stale(1)


def test_update_replaces_removed_pages(tmp_path):
    http = FakeHttp({f"{BASE}/tldr-pages.en.zip": make_zip({"common/old.md": "# old\n"})})
    cache = Cache(tmp_path / "tldr", http, BASE)
    cache.update(["en"])
    http.responses[f"{BASE}/tldr-pages.en.zip"] = make_zip({"common/new.md": "# new\n"})
    cache.update(["en"])
    assert cache.store.names("common", "en") == {"new"}


def test_update_ignores_unsafe_entries(tmp_path):
    http = FakeHttp({f"{BASE}/tldr-pages.en.zip": make_zip({
        "common/ok.md": "ok", "../evil.md": "x", "/abs/evil.md": "x", "a/b/c.md": "x",
    })})
    cache = Cache(tmp_path / "tldr", http, BASE)
    cache.update(["en"])
    assert cache.store.names("common", "en") == {"ok"}
    assert not (tmp_path / "evil.md").exists()


def test_failed_update_keeps_existing_pages(tmp_path):
    http = FakeHttp({f"{BASE}/tldr-pages.en.zip": make_zip({"common/ls.md": "# ls\n"})})
    cache = Cache(tmp_path / "tldr", http, BASE)
    cache.update(["en"])
    http.responses[f"{BASE}/tldr-pages.en.zip"] = b"not a zip"
    (result,) = cache.update(["en"])
    assert result.error
    assert cache.store.read("ls", "common", "en") == "# ls\n"


def test_never_updated_cache_is_stale(tmp_path):
    assert Cache(tmp_path, FakeHttp(), BASE).is_stale(1000)


def test_clear(tmp_path):
    cache = Cache(tmp_path / "tldr", FakeHttp(), BASE)
    assert cache.clear() is False
    (tmp_path / "tldr" / "pages").mkdir(parents=True)
    assert cache.clear() is True
    assert not cache.exists()
