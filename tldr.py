#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""Python command-line client for tldr pages (client specification 2.3)."""

import os
import re
import shutil
import ssl
import sys
import time
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, url2pathname, urlopen
from zipfile import BadZipFile, ZipFile

import shtab
from termcolor import ATTRIBUTES, COLORS, HIGHLIGHTS, colored

__version__ = "4.0.0.dev0"
__client_specification__ = "2.3"

DEFAULT_PAGES_SOURCE = 'https://raw.githubusercontent.com/tldr-pages/tldr/main/pages'
DEFAULT_DOWNLOAD_LOCATION = 'https://github.com/tldr-pages/tldr/releases/latest/download/tldr.zip'
ISSUE_URL = 'https://github.com/tldr-pages/tldr/issues/new?title=page%20request:%20{}'
USER_AGENT = f'tldr-python-client/{__version__}'

OS_DIRECTORIES = {
    "android": "android",
    "darwin": "osx",
    "freebsd": "freebsd",
    "linux": "linux",
    "macos": "osx",
    "netbsd": "netbsd",
    "openbsd": "openbsd",
    "osx": "osx",
    "sunos": "sunos",
    "win32": "windows",
    "windows": "windows"
}

# Platforms known before any page is on disk. New ones (e.g. `dos`, `cisco-ios`)
# are picked up from the pages directories, as the spec recommends.
KNOWN_PLATFORMS = sorted(set(OS_DIRECTORIES.values()) | {'common'})

# Written after every successful cache update: its mtime is the cache age and it
# lists the languages fetched (including those without an archive, like `eo`).
CACHE_STAMP = '.last-update'

# Archive entries look like `linux/ls.md`. Anything else (LICENSE, index
# files, paths trying to escape the cache directory) is skipped.
ARCHIVE_ENTRY = re.compile(r'[a-z0-9][a-z0-9-]*/[^/\\]+\.md')

# A page source is either a local directory that contains `pages`, `pages.it`, ...
# or the URL of a remote `pages` directory (translations at `<url>.it`, ...).
Source = Path | str


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name, '').strip().lower()
    if not value:
        return default
    return value not in ('0', 'false', 'no', 'off')


def env_number(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


# --- Languages ---------------------------------------------------------------

def get_language_code(language: str) -> str | None:
    """`it_IT.UTF-8` -> `it`. Keeps the regional variants that tldr has pages for.

    Returns None for empty values and for `C`/`POSIX`, which the spec ignores.
    """
    language = language.split('.')[0].split('@')[0].strip()
    if language in ('', 'C', 'POSIX'):
        return None
    if language in ('pt_PT', 'pt_BR', 'zh_TW'):
        return language
    if language == 'pt':
        return 'pt_PT'
    return language.split('_')[0]


def get_language_list() -> list[str]:
    """Languages to look pages up in, most preferred first. Always ends with `en`.

    `TLDR_LANGUAGE` goes first. Then the spec algorithm: `LANGUAGE` is only
    honoured when `LANG` is set, and `LANG` comes after it.
    """
    candidates = [os.environ.get('TLDR_LANGUAGE', '')]
    if get_language_code(os.environ.get('LANG', '')):
        candidates += os.environ.get('LANGUAGE', '').split(':')
        candidates.append(os.environ['LANG'])
    candidates.append('en')

    languages = []
    for candidate in candidates:
        code = get_language_code(candidate)
        if code and code not in languages:
            languages.append(code)
    return languages


def pages_dir_name(language: str) -> str:
    return 'pages' if language == 'en' else f'pages.{language}'


# --- Platforms ---------------------------------------------------------------

def get_platform() -> str:
    for key, platform in OS_DIRECTORIES.items():
        if sys.platform.startswith(key):
            return platform
    return 'linux'


def get_all_platforms(sources: list[Source]) -> list[str]:
    platforms = set(KNOWN_PLATFORMS)
    for source in sources:
        if isinstance(source, Path) and (source / 'pages').is_dir():
            platforms |= {entry.name for entry in (source / 'pages').iterdir() if entry.is_dir()}
    return sorted(platforms)


def get_platform_list(first: str, all_platforms: list[str]) -> list[str]:
    """`first`, then `common`, then every other platform: the spec's lookup order."""
    order = [first] if first == 'common' else [first, 'common']
    return order + [platform for platform in all_platforms if platform not in order]


# --- Where pages live ----------------------------------------------------------

def get_cache_dir() -> Path:
    if os.environ.get('XDG_CACHE_HOME'):
        return Path(os.environ['XDG_CACHE_HOME']) / 'tldr'
    if os.environ.get('HOME'):
        return Path(os.environ['HOME']) / '.cache' / 'tldr'
    return Path.home() / '.cache' / 'tldr'


def get_system_cache_dirs() -> list[Path]:
    """Pages installed by distribution packages, e.g. `/usr/share/tldr`."""
    data_dirs = os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share'
    return [Path(entry) / 'tldr' for entry in data_dirs.split(':') if entry]


def get_local_sources() -> list[Path]:
    """The user cache, then system pages: every local directory that has pages."""
    return [path for path in [get_cache_dir(), *get_system_cache_dirs()] if (path / 'pages').is_dir()]


def parse_source(value: str) -> Source:
    """`-s`/`TLDR_PAGES_SOURCE_LOCATION`: a URL, a `file://` URL, or a local path.

    A local path may be a tldr checkout or its `pages` directory.
    """
    url = urlparse(value)
    if url.scheme in ('http', 'https'):
        return value.rstrip('/')
    path = Path(url2pathname(url.path) if url.scheme == 'file' else value).expanduser()
    return path if (path / 'pages').is_dir() else path.parent


def download(url: str) -> bytes:
    context = None
    if env_flag('TLDR_ALLOW_INSECURE', False):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    elif os.environ.get('TLDR_CERT'):
        context = ssl.create_default_context(cafile=Path(os.environ['TLDR_CERT']).expanduser())
    request = Request(url, headers={'User-Agent': USER_AGENT})
    with urlopen(request, timeout=10, context=context) as response:
        return response.read()


def read_page(source: Source, name: str, platform: str, language: str) -> str | None:
    """One page from one source, or None if it isn't there. Network errors propagate."""
    if isinstance(source, Path):
        path = source / pages_dir_name(language) / platform / f'{name}.md'
        try:
            return path.read_text(encoding='utf-8')
        except (FileNotFoundError, NotADirectoryError):
            return None

    base = source if language == 'en' else f'{source}.{language}'
    try:
        return download(f'{base}/{quote(platform)}/{quote(name)}.md').decode('utf-8')
    except HTTPError as error:
        if error.code == 404:
            return None
        raise


def find_page(
    name: str,
    sources: list[Source],
    platforms: list[str],
    languages: list[str]
) -> tuple[str, str] | None:
    """Return `(markdown, platform)` for the best match, or None.

    Platform takes precedence over language (spec "Page resolution"), and
    for each platform/language pair the sources are tried in order.
    """
    for platform in platforms:
        for language in languages:
            for source in sources:
                page = read_page(source, name, platform, language)
                if page is not None:
                    return page, platform
    return None


def get_commands(sources: list[Source], platforms: list[str], languages: list[str]) -> list[str]:
    commands = set()
    for source in sources:
        if not isinstance(source, Path):
            continue
        for platform in platforms:
            for language in languages:
                directory = source / pages_dir_name(language) / platform
                if directory.is_dir():
                    commands |= {page.stem for page in directory.glob('*.md')}
    return sorted(commands)


# --- Cache -------------------------------------------------------------------

def cache_is_stale(languages: list[str]) -> bool:
    """True if the cache is older than `TLDR_CACHE_MAX_AGE` or lacks one of `languages`."""
    stamp = get_cache_dir() / CACHE_STAMP
    try:
        age_hours = (time.time() - stamp.stat().st_mtime) / 3600
        cached = set(stamp.read_text().split())
    except FileNotFoundError:
        return True
    return age_hours > env_number('TLDR_CACHE_MAX_AGE', 24 * 7) or not cached.issuperset(languages)


def update_cache(languages: list[str], verbose: bool = True) -> bool:
    """Download one archive per language and swap it into the cache.

    Each language is extracted next to the cache and renamed into place, so
    pages deleted upstream disappear and an interrupted download never
    leaves a half-written cache. Returns True if any language was updated.
    """
    location = os.environ.get('TLDR_DOWNLOAD_CACHE_LOCATION', DEFAULT_DOWNLOAD_LOCATION)
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    updated = False
    handled = []
    for language in languages:
        url = f"{location.removesuffix('.zip')}-pages.{language}.zip"
        try:
            archive = ZipFile(BytesIO(download(url)))
        except HTTPError as error:
            # Locales without translations (e.g. `eo`) have no archive; that's fine.
            if error.code == 404:
                handled.append(language)
            elif verbose:
                eprint(f"Error: Unable to update cache for language {language} from {url}: {error}")
            continue
        except (URLError, OSError, BadZipFile) as error:
            if verbose:
                eprint(f"Error: Unable to update cache for language {language} from {url}: {error}")
            continue

        target = cache_dir / pages_dir_name(language)
        staging = cache_dir / f'{target.name}.new'
        retired = cache_dir / f'{target.name}.old'
        shutil.rmtree(staging, ignore_errors=True)

        count = 0
        with archive:
            for entry in archive.namelist():
                if ARCHIVE_ENTRY.fullmatch(entry):
                    destination = staging / entry
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(entry))
                    count += 1
        if count == 0:
            shutil.rmtree(staging, ignore_errors=True)
            if verbose:
                eprint(f"Error: The archive for language {language} contained no pages: {url}")
            continue

        shutil.rmtree(retired, ignore_errors=True)
        if target.exists():
            target.rename(retired)
        staging.rename(target)
        shutil.rmtree(retired, ignore_errors=True)
        updated = True
        handled.append(language)
        if verbose:
            eprint(f"Updated cache for language {language}: {count} entries")

    if updated:
        stamp = cache_dir / CACHE_STAMP
        previous = stamp.read_text().split() if stamp.exists() else []
        stamp.write_text('\n'.join(dict.fromkeys(previous + handled)) + '\n')
    return updated


def clear_cache() -> None:
    cache_dir = get_cache_dir()
    if not cache_dir.exists():
        eprint(f"No cache directory found at {cache_dir}")
        return
    shutil.rmtree(cache_dir)
    eprint(f"Cleared cache at {cache_dir}")


# --- Rendering ---------------------------------------------------------------

LEADING_SPACES = '  '

DEFAULT_COLORS = {
    'name': 'bold',
    'description': '',
    'example': 'green',
    'command': 'red',
    'parameter': '',
    'code': 'yellow italic',  # `inline code` in example descriptions
}

INLINE_CODE = re.compile(r'`([^`]+)`')
AUTOLINK = re.compile(r'<([a-z][a-z0-9+.-]*:[^<>\s]+)>', re.IGNORECASE)
OPTION_PLACEHOLDER = re.compile(r'\[(?P<short>[^|\]]+)\|(?P<long>[^\]]+)\]')


def colors_of(key: str) -> tuple[str | None, str | None, list[str]]:
    """Parse `TLDR_COLOR_<KEY>`, e.g. `red on_yellow underline`. Unknown words are ignored."""
    values = os.environ.get(f'TLDR_COLOR_{key.upper()}', DEFAULT_COLORS[key]).split()
    color = None
    on_color = None
    attrs = []
    for value in values:
        if value in COLORS:
            color = value
        elif value in HIGHLIGHTS:
            on_color = value
        elif value in ATTRIBUTES:
            attrs.append(value)
    return color, on_color, attrs


def split_placeholders(command: str, option_style: str = 'long') -> list[tuple[str, bool]]:
    """Split an example command into `(text, is_placeholder)` parts.

    - `{{x}}` is a placeholder; balanced braces inside it are kept (`{{stash@{0}}}`).
    - `\\{\\{` and `\\}\\}` are literal double braces, also inside a placeholder.
    - `{{{x}}` is a literal `{` followed by a placeholder, unless the braces
      balance as one placeholder (`{{{"a": {"b": 1\\}\\}}}`).
    - `{{[-A|--all]}}` becomes plain `-A` or `--all` for the short/long style,
      and stays a placeholder for `both`.
    """
    parts: list[tuple[str, bool]] = []
    text = ''
    i = 0
    while i < len(command):
        if command.startswith(('\\{\\{', '\\}\\}'), i):
            text += command[i + 1] * 2
            i += 4
        elif command.startswith('{{', i):
            end = placeholder_end(command, i + 2)
            if end is None and command.startswith('{{{', i):
                text += '{'
                i += 1
                continue
            if end is None:
                end = command.find('}}', i + 2)
            if end == -1:
                # Never closed: show it as written.
                text += command[i:]
                break
            content = command[i + 2:end].replace('\\{\\{', '{{').replace('\\}\\}', '}}')
            option = OPTION_PLACEHOLDER.fullmatch(content)
            if option and option_style in ('short', 'long'):
                text += option[option_style]
            else:
                if text:
                    parts.append((text, False))
                    text = ''
                parts.append((content, True))
            i = end + 2
        else:
            text += command[i]
            i += 1
    if text:
        parts.append((text, False))
    return parts


def placeholder_end(command: str, start: int) -> int | None:
    """Index of the `}}` closing a placeholder whose content starts at `start`.

    Braces inside must balance (escaped pairs count as two). None if they don't.
    """
    depth = 0
    i = start
    while i < len(command):
        if command.startswith('\\{\\{', i):
            depth += 2
            i += 4
        elif command.startswith('\\}\\}', i):
            depth -= 2
            i += 4
        elif command[i] == '{':
            depth += 1
            i += 1
        elif command[i] == '}':
            if depth == 0 and command.startswith('}}', i):
                return i
            depth -= 1
            i += 1
        else:
            i += 1
        if depth < 0:
            return None
    return None


def render_page(markdown: str, option_style: str = 'long', color: bool = False) -> str:
    styles = {key: colors_of(key) for key in DEFAULT_COLORS} if color else {}

    def paint(key: str, text: str) -> str:
        if not color or not text:
            return text
        return colored(text, *styles[key], force_color=True)

    lines = ['']
    for line in markdown.splitlines():
        line = line.rstrip()
        if not line:
            continue

        if line.startswith('# '):
            lines += [LEADING_SPACES + paint('name', line[2:].strip()), '']

        elif line.startswith('>'):
            # Only autolink brackets go: `a -> b` must stay intact.
            description = AUTOLINK.sub(r'\1', line[1:].strip())
            lines.append(LEADING_SPACES + paint('description', description))

        elif line.startswith('- '):
            # re.split with one group alternates: text, code, text, code, ...
            parts = INLINE_CODE.split(line)
            lines += ['', LEADING_SPACES + ''.join(
                paint('code' if index % 2 else 'example', part) for index, part in enumerate(parts)
            )]

        elif len(line) > 1 and line.startswith('`') and line.endswith('`'):
            lines.append(LEADING_SPACES * 2 + ''.join(
                paint('parameter' if is_placeholder else 'command', text)
                for text, is_placeholder in split_placeholders(line[1:-1], option_style)
            ))

        else:
            # Anything else valid in CommonMark: show it rather than drop it.
            lines.append(LEADING_SPACES + line)
    lines.append('')
    return '\n'.join(lines) + '\n'


def use_color(forced: bool) -> bool:
    if forced:
        return True
    if os.environ.get('NO_COLOR'):
        return False
    if os.environ.get('FORCE_COLOR'):
        return True
    return sys.stdout.isatty()


# --- Command line ------------------------------------------------------------

def create_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="tldr",
        usage="tldr command [options]",
        description="Python command line client for tldr"
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__} (Client Specification {__client_specification__})'
    )
    parser.add_argument('--search', metavar='"KEYWORDS"',
                        help="Search for a specific command from a query")
    parser.add_argument('-u', '--update', '--update_cache', action='store_true',
                        help="Update the local cache of pages and exit")
    parser.add_argument('-k', '--clear-cache', action='store_true',
                        help="Delete the local cache of pages and exit")
    parser.add_argument('-p', '--platform', metavar='PLATFORM',
                        help=f"Override the operating system [{', '.join(KNOWN_PLATFORMS)}, ...]")
    parser.add_argument('-l', '--list', action='store_true',
                        help="List all available commands for operating system")
    parser.add_argument('-s', '--source',
                        help="Read pages from this URL or local `pages` directory instead of the cache")
    parser.add_argument('-c', '--color', action='store_true',
                        help="Override color stripping")
    parser.add_argument('-r', '--render', action='store_true',
                        help='Render local markdown files')
    parser.add_argument('-L', '--language',
                        help='Override the default language')
    parser.add_argument('-m', '--markdown', action='store_true',
                        help='Just print the plain page file.')
    parser.add_argument('-S', '--short-options', action='store_true',
                        help='Display shortform options over longform')
    parser.add_argument('-E', '--long-options', action='store_true',
                        help='Display longform options over shortform')
    parser.add_argument(
        'command', nargs='*', help="command to lookup", metavar='command'
    ).complete = {"bash": "shtab_tldr_cmd_list", "zsh": "shtab_tldr_cmd_list"}

    shtab.add_argument_to(parser, preamble={
        'bash': rf'''shtab_tldr_cmd_list(){{
          compgen -W "$("{sys.executable}" -m tldr --list)" -- "$1"
        }}''',
        'zsh': rf'''shtab_tldr_cmd_list(){{
          _describe 'command' "($("{sys.executable}" -m tldr --list))"
        }}'''
    })
    return parser


def get_sources(source: str | None, languages: list[str]) -> list[Source]:
    """Where to read pages from, refreshing the cache first if it is stale."""
    if source:
        return [parse_source(source)]

    remote = parse_source(os.environ.get('TLDR_PAGES_SOURCE_LOCATION', DEFAULT_PAGES_SOURCE))
    if not env_flag('TLDR_CACHE_ENABLED', True):
        return [remote]

    network = env_flag('TLDR_NETWORK_ENABLED', True)
    wanted = list(dict.fromkeys(get_language_list() + languages))
    if network and cache_is_stale(wanted):
        first_download = not (get_cache_dir() / 'pages').is_dir()
        if first_download:
            eprint(f"Downloading tldr pages to {get_cache_dir()} ...")
        if not update_cache(wanted, verbose=first_download) and not first_download:
            eprint("Warning: Could not refresh the cache, using the existing pages.")

    # Without any local pages (e.g. GitHub releases are blocked), fetch single pages.
    return get_local_sources() or ([remote] if network else [])


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    options = parser.parse_args(argv)

    if options.language:
        languages = [get_language_code(options.language) or 'en']
    else:
        languages = get_language_list()

    if options.clear_cache:
        clear_cache()
        return 0
    if options.update:
        updated = update_cache(list(dict.fromkeys(get_language_list() + languages)))
        if not (options.command or options.list or options.search):
            return 0 if updated else 1
    if not (options.command or options.list or options.search):
        parser.print_help(sys.stderr)
        return 1

    option_style = os.environ.get('TLDR_OPTIONS', 'long').strip().lower()
    if option_style not in ('short', 'long', 'both'):
        option_style = 'long'
    if options.short_options and options.long_options:
        option_style = 'both'
    elif options.short_options:
        option_style = 'short'
    elif options.long_options:
        option_style = 'long'

    color = use_color(options.color)

    if options.render:
        status = 0
        for path in options.command:
            try:
                markdown = Path(path).read_text(encoding='utf-8')
            except OSError as error:
                eprint(f"Error: {path}: {error.strerror}")
                status = 1
                continue
            sys.stdout.write(markdown if options.markdown else render_page(markdown, option_style, color))
        return status

    sources = get_sources(options.source, languages)
    if not sources:
        eprint("Error: No pages available offline. Connect to the internet and run `tldr --update`.")
        return 1
    if isinstance(sources[0], Path) and not (sources[0] / 'pages').is_dir():
        eprint(f"Error: {options.source} is not a tldr pages directory.")
        return 1

    all_platforms = get_all_platforms(sources)
    platform = get_platform()
    requested = (options.platform or os.environ.get('TLDR_PLATFORM', '')).strip().lower()
    if requested:
        requested = OS_DIRECTORIES.get(requested, requested)
        if requested in all_platforms:
            platform = requested
        elif options.platform:
            eprint(f"Error: Unknown platform '{options.platform}'. Choose from: {', '.join(all_platforms)}")
            return 1
        else:
            eprint(f"Warning: '{requested}' is not a supported TLDR_PLATFORM environment value."
                   "\nFalling back to auto-detection.")
    platforms = get_platform_list(platform, all_platforms)

    if options.list:
        local = [source for source in sources if isinstance(source, Path)] or get_local_sources()
        print('\n'.join(get_commands(local, platforms[:2], languages)))
        return 0

    if options.search:
        local = [source for source in sources if isinstance(source, Path)] or get_local_sources()
        commands = get_commands(local, platforms, languages)
        if not commands:
            eprint("Update cache, no commands to check from.")
            return 1
        matches = [command for command in commands if options.search.lower() in command.lower()]
        if not matches:
            eprint("No commands matched your search term.")
            return 1
        print('\n'.join(matches))
        return 0

    command = '-'.join(options.command).lower()
    try:
        result = find_page(command, sources, platforms, languages)
    except URLError as error:
        local = get_local_sources()
        if options.source or not local:
            eprint(f"Error fetching from tldr: {error}")
            return 1
        eprint(f"Warning: Error fetching from tldr ({error}), using the cache instead.")
        sources = local
        result = find_page(command, sources, platforms, languages)

    if result is None:
        if options.language:
            eprint(f"`{command}` documentation is not available in language `{options.language}`.")
        else:
            eprint(f"`{command}` documentation is not available.")
        eprint(f"You can request it here: {ISSUE_URL.format(quote(command))}")
        return 1

    page, found_on = result
    sys.stdout.write(page if options.markdown else render_page(page, option_style, color))

    if found_on not in (platform, 'common'):
        eprint(f"Warning: showing page from platform '{found_on}', "
               f"because '{command}' does not exist in '{platform}' and 'common'.")
    # Probing every platform is free on disk but costs a request each over the network.
    if all(isinstance(source, Path) for source in sources):
        others = [other for other in platforms
                  if other != found_on and find_page(command, sources, [other], languages)]
        if others:
            eprint(f"Also available on: {', '.join(others)}.")
    return 0


def cli() -> None:
    if sys.platform == "win32":
        import colorama
        colorama.just_fix_windows_console()
    for stream in (sys.stdout, sys.stderr):
        # Pages are UTF-8; don't crash on consoles or pipes that can't show a character.
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='replace')
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        eprint("\nExited on keyboard interrupt.")
        sys.exit(130)


if __name__ == "__main__":
    cli()
