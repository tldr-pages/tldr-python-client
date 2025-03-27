#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import sys
import os
import re
from argparse import ArgumentParser
from pathlib import Path
from zipfile import ZipFile
from datetime import datetime
from io import BytesIO
from typing import List, Optional, Tuple, Union
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from termcolor import colored
import ssl
import shtab
import shutil

__version__ = "3.4.0"
__client_specification__ = "2.3"

REQUEST_HEADERS = {'User-Agent': 'tldr-python-client'}
PAGES_SOURCE_LOCATION = os.environ.get(
    'TLDR_PAGES_SOURCE_LOCATION',
    'https://raw.githubusercontent.com/tldr-pages/tldr/main/pages'
).rstrip('/')
DOWNLOAD_CACHE_LOCATION = os.environ.get(
    'TLDR_DOWNLOAD_CACHE_LOCATION',
    'https://github.com/tldr-pages/tldr/releases/latest/download/tldr.zip'
)

USE_NETWORK = int(os.environ.get('TLDR_NETWORK_ENABLED', '1')) > 0
USE_CACHE = int(os.environ.get('TLDR_CACHE_ENABLED', '1')) > 0
MAX_CACHE_AGE = int(os.environ.get('TLDR_CACHE_MAX_AGE', 24*7))
CAFILE = None if os.environ.get('TLDR_CERT', None) is None else \
    Path(os.environ.get('TLDR_CERT')).expanduser()

URLOPEN_CONTEXT = None
if int(os.environ.get('TLDR_ALLOW_INSECURE', '0')) == 1:
    URLOPEN_CONTEXT = ssl.create_default_context()
    URLOPEN_CONTEXT.check_hostname = False
    URLOPEN_CONTEXT.verify_mode = ssl.CERT_NONE
elif CAFILE:
    URLOPEN_CONTEXT = ssl.create_default_context(cafile=CAFILE)

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


class CacheNotExist(Exception):
    pass


def get_language_code(language: str) -> str:
    language = language.split('.')[0]
    if language in ['pt_PT', 'pt_BR', 'zh_TW']:
        return language
    elif language == "pt":
        return "pt_PT"
    return language.split('_')[0]


def get_default_language() -> str:
    default_lang = get_language_code(
        os.environ.get(
            'LANG',
            'C'
        )
    )

    if default_lang == 'C' or default_lang == 'POSIX':
        default_lang = None

    return default_lang


def get_cache_dir() -> Path:
    if os.environ.get('XDG_CACHE_HOME', False):
        return Path(os.environ.get('XDG_CACHE_HOME')) / 'tldr'
    if os.environ.get('HOME', False):
        return Path(os.environ.get('HOME')) / '.cache' / 'tldr'
    return Path.home() / '.cache' / 'tldr'


def get_cache_file_path(command: str, platform: str, language: str) -> Path:
    pages_dir = "pages"
    if language and language != 'en':
        pages_dir += "." + language
    return get_cache_dir() / pages_dir / platform / f"{command}.md"


def load_page_from_cache(command: str, platform: str, language: str) -> Optional[str]:
    try:
        with get_cache_file_path(
            command,
            platform,
            language
        ).open('rb') as cache_file:
            cache_file_contents = cache_file.read()
        return cache_file_contents
    except Exception:
        pass


def store_page_to_cache(
    page: str,
    command: str,
    platform: str,
    language: str
) -> Optional[str]:
    try:
        cache_file_path = get_cache_file_path(command, platform, language)
        cache_file_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_file_path.open("wb") as cache_file:
            cache_file.write(page)
    except Exception:
        pass


def have_recent_cache(command: str, platform: str, language: str) -> bool:
    try:
        cache_file_path = get_cache_file_path(command, platform, language)
        last_modified = datetime.fromtimestamp(cache_file_path.stat().st_mtime)
        hours_passed = (datetime.now() - last_modified).total_seconds() / 3600
        return hours_passed <= MAX_CACHE_AGE
    except Exception:
        return False


def get_page_url(command: str, platform: str, remote: str, language: str) -> str:
    if remote is None:
        remote = PAGES_SOURCE_LOCATION

    if language is None or language == 'en':
        language = ''
    else:
        language = '.' + language

    return remote + language + "/" + platform + "/" + quote(command) + ".md"


def get_page_for_platform(
    command: str,
    platform: str,
    remote: str,
    language: str,
    only_use_cache: bool = False
) -> str:
    data_downloaded = False
    if USE_CACHE and have_recent_cache(command, platform, language):
        data = load_page_from_cache(command, platform, language)
    elif only_use_cache:
        raise CacheNotExist("Cache for {} in {} not Found".format(
            command,
            platform,
        ))
    else:
        page_url = get_page_url(command, platform, remote, language)
        try:
            data = urlopen(
                Request(page_url, headers=REQUEST_HEADERS),
                timeout=10,
                context=URLOPEN_CONTEXT
            ).read()
            data_downloaded = True
        except Exception:
            if not USE_CACHE:
                raise
            data = load_page_from_cache(command, platform, language)
            if data is None:
                raise
    if data_downloaded and USE_CACHE:
        store_page_to_cache(data, command, platform, language)
    return data.splitlines()


def update_page_for_platform(
    command: str,
    platform: str,
    remote: str,
    language: str
) -> None:
    page_url = get_page_url(platform, command, remote, language)
    data = urlopen(
        Request(page_url, headers=REQUEST_HEADERS),
        context=URLOPEN_CONTEXT
    ).read()
    store_page_to_cache(data, command, platform, language)


def get_platform() -> str:
    for key in OS_DIRECTORIES:
        if sys.platform.startswith(key):
            return OS_DIRECTORIES[key]
    return 'linux'


def get_platform_list() -> List[str]:
    platforms = ['common'] + list(set(OS_DIRECTORIES.values()))
    current_platform = get_platform()
    platforms.remove(current_platform)
    platforms.insert(0, current_platform)
    return platforms


def get_language_list() -> List[str]:
    tldr_language = get_language_code(os.environ.get('TLDR_LANGUAGE', ''))
    languages = os.environ.get('LANGUAGE', '').split(':')
    languages = list(map(
        get_language_code,
        filter(lambda x: not (x == 'C' or x == 'POSIX' or x == ''), languages)
    ))

    default_lang = get_default_language()

    if default_lang is None:
        languages = []
    elif default_lang not in languages:
        languages.append(default_lang)
    if tldr_language:
        # remove tldr_language if it already exists to avoid double entry
        try:
            languages.remove(tldr_language)
        except ValueError:
            pass
        languages.insert(0, tldr_language)
    if 'en' not in languages:
        languages.append('en')
    return languages


def get_page_for_every_platform(
    command: str,
    remote: Optional[str] = None,
    platforms: Optional[List[str]] = None,
    languages: Optional[List[str]] = None
) -> Union[List[Tuple[str, str]], bool]:
    """Gives a list of tuples result-platform ordered by priority."""
    if platforms is None:
        platforms = get_platform_list()
    if languages is None:
        languages = get_language_list()
    # only use cache
    if USE_CACHE:
        result = list()
        for platform in platforms:
            for language in languages:
                if platform is None:
                    continue
                try:
                    result.append(
                        (get_page_for_platform(
                                command,
                                platform,
                                remote,
                                language,
                                only_use_cache=True,
                        ), platform)
                    )
                    break   # Don't want to look for the same page in other langs
                except CacheNotExist:
                    continue
        if result:  # Return if smth was found
            return result
    # Know here that we don't have the info in cache
    result = list()
    for platform in platforms:
        for language in languages:
            if platform is None:
                continue
            try:
                result.append(
                    (
                        get_page_for_platform(
                            command,
                            platform,
                            remote,
                            language
                        ),
                        platform
                    )
                )
                break
            except HTTPError as err:
                if err.code != 404:
                    raise
            except URLError:
                if not PAGES_SOURCE_LOCATION.startswith('file://'):
                    raise
    if result:  # Return if smth was found
        return result

    return False


def get_page(
    command: str,
    remote: Optional[str] = None,
    platforms: Optional[List[str]] = None,
    languages: Optional[List[str]] = None
) -> Union[str, bool]:
    if platforms is None:
        platforms = get_platform_list()
    if languages is None:
        languages = get_language_list()
    # only use cache
    if USE_CACHE:
        for platform in platforms:
            for language in languages:
                if platform is None:
                    continue
                try:
                    return get_page_for_platform(
                        command,
                        platform,
                        remote,
                        language,
                        only_use_cache=True,
                    )
                except CacheNotExist:
                    continue
    for platform in platforms:
        for language in languages:
            if platform is None:
                continue
            try:
                return get_page_for_platform(command, platform, remote, language)
            except HTTPError as err:
                if err.code != 404:
                    raise
            except URLError:
                if not PAGES_SOURCE_LOCATION.startswith('file://'):
                    raise

    return False


DEFAULT_COLORS = {
    'name': 'bold',
    'description': '',
    'example': 'green',
    'command': 'red',
    'parameter': ''
}

# See more details in the README:
# https://github.com/tldr-pages/tldr-python-client#colors
ACCEPTED_COLORS = [
    'blue', 'green', 'yellow', 'cyan', 'magenta', 'white', 'grey', 'red'
]

ACCEPTED_COLOR_BACKGROUNDS = [
    'on_blue', 'on_cyan', 'on_magenta', 'on_white',
    'on_grey', 'on_yellow', 'on_red', 'on_green'
]

ACCEPTED_COLOR_ATTRS = [
    'reverse', 'blink', 'dark', 'concealed', 'underline', 'bold'
]

LEADING_SPACES_NUM = 2

EXAMPLE_SPLIT_REGEX = re.compile(r'(?P<example>`.+?`)')
EXAMPLE_REGEX = re.compile(r'(?:`)(?P<example>.+?)(?:`)')
COMMAND_SPLIT_REGEX = re.compile(r'(?P<param>{{.+?}*}})')
PARAM_REGEX = re.compile(r'(?:{{)(?P<param>.+?)(?:}})')


def get_commands(platforms: Optional[List[str]] = None,
                 language: Optional[str] = None) -> List[str]:
    if platforms is None:
        platforms = get_platform_list()

    if language:
        languages = [get_language_code(language[0])]
    else:
        languages = get_language_list()

    commands = []
    if get_cache_dir().exists():
        for platform in platforms:
            for language in languages:
                pages_dir = f'pages.{language}' if language != 'en' else 'pages'
                path = get_cache_dir() / pages_dir / platform
                if not path.exists():
                    continue
                commands += [f"{file.stem} ({language})"
                             for file in path.iterdir()
                             if file.suffix == '.md']
    return commands


def colors_of(key: str) -> Tuple[str, str, List[str]]:
    env_key = 'TLDR_COLOR_%s' % key.upper()
    values = os.environ.get(env_key, DEFAULT_COLORS[key]).strip().split()
    color = None
    on_color = None
    attrs = []
    for value in values:
        if value in ACCEPTED_COLORS:
            color = value
        elif value in ACCEPTED_COLOR_BACKGROUNDS:
            on_color = value
        elif value in ACCEPTED_COLOR_ATTRS:
            attrs.append(value)
    return (color, on_color, attrs)


def output(page: str, display_option_length: str, plain: bool = False) -> None:
    def emphasise_example(x: str) -> str:
        # Use ANSI escapes to enable italics at the start and disable at the end
        # Also use the color yellow to differentiate from the default green
        return "\x1B[3m" + colored(x.group('example'), 'yellow') + "\x1B[23m"

    if not plain:
        print()
    for line in page:
        line = line.rstrip().decode('utf-8')

        if plain:
            print(line)
            continue

        elif len(line) == 0:
            continue

        # Handle the command name
        elif line[0] == '#':
            line = ' ' * LEADING_SPACES_NUM + \
                colored(line.replace('# ', ''), *colors_of('name')) + '\n'
            sys.stdout.buffer.write(line.encode('utf-8'))

        # Handle the command description
        elif line[0] == '>':
            line = ' ' * (LEADING_SPACES_NUM - 1) + \
                colored(
                    line.replace('>', '').replace('<', ''),
                    *colors_of('description')
                )
            sys.stdout.buffer.write(line.encode('utf-8'))

        # Handle an example description
        elif line[0] == '-':

            # Stylize text within backticks using yellow italics
            if '`' in line:
                elements = ['\n', ' ' * LEADING_SPACES_NUM]

                for item in EXAMPLE_SPLIT_REGEX.split(line):
                    item, replaced = EXAMPLE_REGEX.subn(emphasise_example, item)
                    if not replaced:
                        item = colored(item, *colors_of('example'))
                    elements.append(item)

                line = ''.join(elements)

            # Otherwise, use the same colour for the whole line
            else:
                line = '\n' + ' ' * LEADING_SPACES_NUM + \
                    colored(line, *colors_of('example'))

            sys.stdout.buffer.write(line.encode('utf-8'))

        # Handle an example command
        elif line[0] == '`':
            line = line[1:-1]  # Remove backticks for parsing

            # Handle escaped placeholders first
            line = line.replace(r'\{\{', '__ESCAPED_OPEN__')
            line = line.replace(r'\}\}', '__ESCAPED_CLOSE__')

            # Extract long or short options from placeholders
            if display_option_length == "short":
                line = re.sub(r'{{\[([^|]+)\|[^|]+?\]}}', r'\1', line)
            elif display_option_length == "long":
                line = re.sub(r'{{\[[^|]+\|([^|]+?)\]}}', r'\1', line)

            elements = [' ' * 2 * LEADING_SPACES_NUM]
            for item in COMMAND_SPLIT_REGEX.split(line):
                item, replaced = PARAM_REGEX.subn(
                    lambda x: colored(x.group('param'), *colors_of('parameter')),
                    item)
                if not replaced:
                    item = colored(item, *colors_of('command'))
                elements.append(item)

            line = ''.join(elements)

            # Restore escaped placeholders
            line = line.replace('__ESCAPED_OPEN__', '{{')
            line = line.replace('__ESCAPED_CLOSE__', '}}')

            sys.stdout.buffer.write(line.encode('utf-8'))
        print()
    print()


def update_cache(language: Optional[List[str]] = None) -> None:
    languages = get_language_list()
    if language and language[0] not in languages:
        languages.append(language[0])
    for language in languages:
        try:
            cache_location = f"{DOWNLOAD_CACHE_LOCATION[:-4]}-pages.{language}.zip"
            req = urlopen(Request(
                cache_location,
                headers=REQUEST_HEADERS
            ), context=URLOPEN_CONTEXT)
            zipfile = ZipFile(BytesIO(req.read()))
            pattern = re.compile(r"(.+)/(.+)\.md")
            cached = 0
            for entry in zipfile.namelist():
                match = pattern.match(entry)
                if match:
                    store_page_to_cache(
                        zipfile.read(entry),
                        match.group(2),
                        match.group(1),
                        language
                    )
                    cached += 1
            print(
                "Updated cache for language "
                f"{language}: {cached} entries"
            )
        except Exception:
            print(
                "Error: Unable to update cache for language "
                f"{language} from {cache_location}"
            )


def clear_cache(language: Optional[List[str]] = None) -> None:
    languages = get_language_list()
    if language and language[0] not in languages:
        languages.append(language[0])
    for language in languages:
        pages_dir = f'pages.{language}' if language != 'en' else 'pages'
        cache_dir = get_cache_dir() / pages_dir
        if cache_dir.exists() and cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir)
                print(f"Cleared cache for language {language}")
            except Exception as e:
                print(f"Error: Unable to delete cache directory {cache_dir}: {e}")
        else:
            print(f"No cache directory found for language {language}")


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="tldr",
        usage="tldr command [options]",
        description="Python command line client for tldr"
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s {} (Client Specification {})'.format(
            __version__,
            __client_specification__
        )
    )

    parser.add_argument("--search",
                        metavar='"KEYWORDS"',
                        type=str,
                        help="Search for a specific command from a query")

    parser.add_argument('-u', '--update', '--update_cache',
                        action='store_true',
                        help="Update the local cache of pages and exit")

    parser.add_argument('-k', '--clear-cache',
                        action='store_true',
                        help="Delete the local cache of pages and exit")

    parser.add_argument(
        '-p', '--platform',
        nargs=1,
        default=None,
        type=str,
        choices=['android', 'freebsd', 'linux', 'netbsd', 'openbsd', 'osx', 'sunos',
                 'windows', 'common'],
        metavar='PLATFORM',
        help="Override the operating system "
             "[android, freebsd, linux, netbsd, openbsd,"
             " osx, sunos, windows, common]"
    )

    parser.add_argument('-l', '--list',
                        default=False,
                        action='store_true',
                        help="List all available commands for operating system")

    parser.add_argument('-s', '--source',
                        default=PAGES_SOURCE_LOCATION,
                        type=str,
                        help="Override the default page source")

    parser.add_argument('-c', '--color',
                        default=None,
                        action='store_const',
                        const=False,
                        help="Override color stripping")

    parser.add_argument('-r', '--render',
                        default=False,
                        action='store_true',
                        help='Render local markdown files'
                        )

    parser.add_argument('-L', '--language',
                        nargs=1,
                        default=None,
                        type=str,
                        help='Override the default language')

    parser.add_argument('-m', '--markdown',
                        default=False,
                        action='store_true',
                        help='Just print the plain page file.')

    parser.add_argument('--short-options',
                        default=False,
                        action="store_true",
                        help='Display shortform options over longform')

    parser.add_argument('--long-options',
                        default=False,
                        action="store_true",
                        help='Display longform options over shortform')

    parser.add_argument(
        'command', type=str, nargs='*', help="command to lookup", metavar='command'
    ).complete = {"bash": "shtab_tldr_cmd_list", "zsh": "shtab_tldr_cmd_list"}

    shtab.add_argument_to(parser, preamble={
        'bash': r'''shtab_tldr_cmd_list(){{
          compgen -W "$("{py}" -m tldr --list | sed 's/[^[:alnum:]_]/ /g')" -- "$1"
        }}'''.format(py=sys.executable),
        'zsh': r'''shtab_tldr_cmd_list(){{
          _describe 'command' "($("{py}" -m tldr --list | sed 's/[^[:alnum:]_]/ /g'))"
        }}'''.format(py=sys.executable)
    })

    return parser


def main() -> None:
    parser = create_parser()

    options = parser.parse_args()

    display_option_length = "long"
    if not (options.short_options or options.long_options):
        if os.environ.get('TLDR_OPTIONS') == "short":
            display_option_length = "short"
        elif os.environ.get('TLDR_OPTIONS') == "long":
            display_option_length = "long"
        elif os.environ.get('TLDR_OPTIONS') == "both":
            display_option_length = "both"
    if options.short_options:
        display_option_length = "short"
    if options.long_options:
        display_option_length = "long"
    if options.short_options and options.long_options:
        display_option_length = "both"
    if sys.platform == "win32":
        import colorama
        colorama.init(strip=options.color)

    if options.color is False:
        os.environ["FORCE_COLOR"] = "true"

    if options.update:
        update_cache(language=options.language)
        return
    elif len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    if options.clear_cache:
        clear_cache(language=options.language)
        return
    elif len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    if options.list:
        print('\n'.join(get_commands(options.platform, options.language)))
    elif options.render:
        for command in options.command:
            file_path = Path(command)
            if file_path.exists():
                with file_path.open(encoding='utf-8') as open_file:
                    output(open_file.read().encode('utf-8').splitlines(),
                           display_option_length,
                           plain=options.markdown)
    elif options.search:
        search_term = options.search.lower()
        commands = get_commands(options.platform, options.language)
        if not commands:
            print("Update cache, no commands to check from.")
            return
        similar_commands = []
        for command in commands:
            if search_term in command.lower():
                similar_commands.append(command)
        if similar_commands:
            print("Similar commands found:")
            print('\n'.join(similar_commands))
            return
        else:
            print("No commands matched your search term.")
    else:
        try:
            command = '-'.join(options.command).lower()
            results = get_page_for_every_platform(
                command,
                options.source,
                options.platform,
                options.language
            )
            if not results:
                sys.exit((
                    "`{cmd}` documentation is not available.\n"
                    "If you want to contribute it, feel free to"
                    " send a pull request to: https://github.com/tldr-pages/tldr"
                ).format(cmd=command))
            else:
                output(results[0][0], display_option_length, plain=options.markdown)
                if results[1:]:
                    platforms_str = [result[1] for result in results[1:]]
                    are_multiple_platforms = len(platforms_str) > 1
                    if are_multiple_platforms:
                        print(
                            f"Found {len(platforms_str)} pages with the same name"
                            f" under the platforms: {', '.join(platforms_str)}."
                        )
                    else:
                        print(
                            f"Found 1 page with the same name"
                            f" under the platform: {platforms_str[0]}."
                        )
        except URLError as e:
            sys.exit("Error fetching from tldr: {}".format(e))


def cli() -> None:
    try:
        main()
    except KeyboardInterrupt:
        print("\nExited on keyboard interrupt.")


if __name__ == "__main__":
    cli()
