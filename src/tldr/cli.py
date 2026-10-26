"""Command-line interface."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO
from urllib.parse import quote, urlparse
from urllib.request import url2pathname

from tldr import __client_specification__, __version__, languages, platforms
from tldr.cache import Cache
from tldr.http import Http, NetworkError
from tldr.render import Theme, render_page
from tldr.resolver import Resolver, page_name
from tldr.settings import Settings
from tldr.stores import DirectoryStore, PageStore, RemoteStore

ISSUE_URL = "https://github.com/tldr-pages/tldr/issues/new?title=page%20request:%20{}"


class UsageError(Exception):
    """Something the user can fix; printed without a traceback, exit code 1."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tldr",
        usage="tldr [options] command...",
        description="Python command-line client for tldr-pages.",
    )
    command = parser.add_argument("command", nargs="*", help="Page to show, e.g. `tar` or `git checkout`")
    parser.add_argument(
        "-v", "--version", action="version",
        version=f"%(prog)s {__version__} (Client Specification {__client_specification__})",
    )
    parser.add_argument("-p", "--platform", help="Look on this platform first (linux, osx, windows, common, ...)")
    parser.add_argument("-L", "--language", help="Show pages only in this language")
    parser.add_argument("-u", "--update", "--update_cache", action="store_true",
                        help="Update the offline cache (then show the page, if one is given)")
    parser.add_argument("-k", "--clear-cache", action="store_true", help="Delete the offline cache and exit")
    parser.add_argument("-l", "--list", action="store_true", help="List pages for the platform")
    parser.add_argument("--search", metavar="KEYWORD", help="List pages whose name contains KEYWORD")
    parser.add_argument("-s", "--source", help="Read pages from this `pages` directory or URL instead of the cache")
    parser.add_argument("-r", "--render", action="store_true", help="Treat arguments as Markdown files to render")
    parser.add_argument("-m", "--markdown", action="store_true", help="Print the raw Markdown of the page")
    parser.add_argument("-c", "--color", action="store_true", help="Use colors even when not writing to a terminal")
    parser.add_argument("-S", "--short-options", action="store_true", help="Show short forms of options")
    parser.add_argument("-E", "--long-options", action="store_true", help="Show long forms of options")

    try:
        import shtab
    except ImportError:
        pass
    else:
        command.complete = {"bash": "_tldr_pages", "zsh": "_tldr_pages"}
        shtab.add_argument_to(parser, preamble={
            "bash": f'_tldr_pages() {{ compgen -W "$("{sys.executable}" -m tldr --list)" -- "$1"; }}',
            "zsh": f"_tldr_pages() {{ _describe 'page' \"($(\"{sys.executable}\" -m tldr --list))\"; }}",
        })
    return parser


class App:
    def __init__(self, args: argparse.Namespace, settings: Settings, env: Mapping[str, str],
                 stdout: TextIO, stderr: TextIO):
        self.args = args
        self.settings = settings
        self.stdout = stdout
        self.stderr = stderr
        self.http = Http(allow_insecure=settings.allow_insecure, cafile=settings.cafile)
        self.cache = Cache(settings.cache_dir, self.http, settings.archive_base_url)

        if args.language:
            self.languages = languages.strict(args.language)
        else:
            self.languages = languages.from_environment(env, settings.language)

        if args.short_options and args.long_options:
            self.option_style = "both"
        elif args.short_options:
            self.option_style = "short"
        elif args.long_options:
            self.option_style = "long"
        else:
            self.option_style = settings.option_style

        self.theme = Theme(settings.colors, color=_use_color(args.color, stdout, env))

    # --- actions ----------------------------------------------------------

    def run(self) -> int:
        args = self.args
        if args.clear_cache:
            cleared = self.cache.clear()
            self.info(f"Cleared {self.cache.directory}" if cleared else "Nothing to clear.")
            return 0
        if args.update:
            updated = self.update_cache(report=True)
            # `tldr -u tar` updates first, then shows the page.
            if not (args.command or args.list or args.search is not None):
                return 0 if updated else 1
        if args.render:
            return self.render_files(args.command)
        if args.list:
            return self.list_pages()
        if args.search is not None:
            return self.search(args.search)
        return self.show(page_name(args.command))

    def show(self, name: str) -> int:
        resolver = self.resolver()
        page = resolver.find(name)
        if page is None:
            return self.not_found(name)

        self.write_page(page.text)

        first = resolver.platforms[0]
        if page.platform not in (first, platforms.COMMON):
            self.warn(f"showing the `{page.platform}` page, because `{name}` "
                      f"does not exist for `{first}` or `{platforms.COMMON}`.")
        if others := resolver.other_platforms(name, page):
            self.info(f"`{name}` also exists for: {', '.join(others)}.")
        return 0

    def list_pages(self) -> int:
        resolver = self.resolver()
        names = resolver.names(list(dict.fromkeys([resolver.platforms[0], platforms.COMMON])))
        self.stdout.write("".join(f"{name}\n" for name in names))
        return 0

    def search(self, keyword: str) -> int:
        resolver = self.resolver()
        keyword = keyword.lower()
        matches = [name for name in resolver.names(resolver.platforms) if keyword in name]
        if not matches:
            self.info(f"No pages match `{keyword}`.")
            return 1
        self.stdout.write("".join(f"{name}\n" for name in matches))
        return 0

    def render_files(self, paths: Sequence[str]) -> int:
        status = 0
        for path in paths:
            try:
                self.write_page(Path(path).read_text(encoding="utf-8"))
            except OSError as error:
                self.error(f"{path}: {error.strerror}")
                status = 1
        return status

    def update_cache(self, report: bool) -> bool:
        """Download pages for the user's languages (and English). True if any succeeded."""
        wanted = self.languages if "en" in self.languages else [*self.languages, "en"]
        updated = False
        for result in self.cache.update(wanted):
            if result.error is None:
                updated = True
                if report:
                    self.info(f"Updated `{result.language}`: {result.pages} pages.")
            elif result.error != "not found" and report:
                self.error(f"could not update `{result.language}`: {result.error}")
        return updated

    # --- helpers ----------------------------------------------------------

    def resolver(self) -> Resolver:
        stores = self.stores()
        available = set(platforms.KNOWN).union(*(store.platforms() for store in stores))

        requested = self.args.platform or self.settings.platform
        if requested:
            first = platforms.normalize(requested)
            if first not in available:
                choices = ", ".join(sorted(available))
                if self.args.platform:
                    raise UsageError(f"unknown platform `{requested}`; choose from: {choices}")
                self.warn(f"ignoring unknown TLDR_PLATFORM `{requested}`.")
                first = platforms.host()
        else:
            first = platforms.host()

        return Resolver(stores, platforms.lookup_order(first, available), self.languages)

    def stores(self) -> list[PageStore]:
        source = self.args.source or self.settings.pages_source
        if source:
            return [self._source_store(source)]

        if self.settings.network_enabled and self.cache.is_stale(self.settings.cache_max_age_hours):
            first_download = not self.cache.exists()
            if first_download:
                self.info("Downloading pages for offline use...")
            if not self.update_cache(report=first_download) and not first_download:
                self.warn("could not refresh the offline pages; using the existing ones.")

        system = [DirectoryStore(path) for path in self.settings.system_dirs if (path / "pages").is_dir()]
        if self.cache.exists():
            return [self.cache.store, *system]
        if system:
            return system
        raise UsageError("no pages available offline; connect to the internet and run `tldr --update`")

    def _source_store(self, source: str) -> PageStore:
        url = urlparse(source)
        if url.scheme in ("http", "https"):
            return RemoteStore(source, self.http)
        path = Path(url2pathname(url.path) if url.scheme == "file" else source).expanduser()
        # Accept both the repository root and its `pages` directory.
        root = path if (path / "pages").is_dir() else path.parent
        if not (root / "pages").is_dir():
            raise UsageError(f"`{source}` is not a tldr `pages` directory")
        return DirectoryStore(root)

    def write_page(self, markdown: str) -> None:
        if self.args.markdown:
            self.stdout.write(markdown if markdown.endswith("\n") else markdown + "\n")
        else:
            self.stdout.write(render_page(markdown, self.option_style, self.theme))

    def not_found(self, name: str) -> int:
        if self.args.language:
            self.error(f"page `{name}` is not available in `{self.args.language}`.")
        else:
            self.error(f"page `{name}` not found.")
        self.info(f"You can request it: {ISSUE_URL.format(quote(name))}")
        return 1

    def info(self, message: str) -> None:
        print(message, file=self.stderr)

    def warn(self, message: str) -> None:
        print(f"warning: {message}", file=self.stderr)

    def error(self, message: str) -> None:
        print(f"error: {message}", file=self.stderr)


def _use_color(forced: bool, stream: TextIO, env: Mapping[str, str]) -> bool:
    if forced:
        return True
    if env.get("NO_COLOR"):
        return False
    if env.get("FORCE_COLOR"):
        return True
    return hasattr(stream, "isatty") and stream.isatty()


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None,
         stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    env = os.environ if env is None else env
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    parser = build_parser()
    args = parser.parse_args(argv)
    if not (args.command or args.update or args.clear_cache or args.list or args.search is not None):
        parser.print_help(stderr)
        return 1
    try:
        return App(args, Settings.from_env(env), env, stdout, stderr).run()
    except UsageError as error:
        print(f"error: {error}", file=stderr)
        return 1
    except NetworkError as error:
        print(f"error: {error}", file=stderr)
        return 1


def run() -> None:
    if sys.platform == "win32":
        try:
            from colorama import just_fix_windows_console
            just_fix_windows_console()
        except ImportError:
            pass
    for stream in (sys.stdout, sys.stderr):
        # Pages are UTF-8; don't crash on terminals or pipes that can't show a character.
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
