#!/usr/bin/env python3

import sys
import os
import re
from argparse import ArgumentParser
from zipfile import ZipFile
from datetime import datetime
from io import BytesIO
import ssl
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from termcolor import colored
import colorama  # Required for Windows

__version__ = "1.0.0"
__client_specification__ = "1.2"

REQUEST_HEADERS = {'User-Agent': 'tldr-python-client'}
PAGES_SOURCE_LOCATION = os.environ.get(
    'TLDR_PAGES_SOURCE_LOCATION',
    'https://raw.githubusercontent.com/tldr-pages/tldr/master/pages'
).rstrip('/')
DOWNLOAD_CACHE_LOCATION = os.environ.get(
    'TLDR_DOWNLOAD_CACHE_LOCATION',
    'https://tldr-pages.github.io/assets/tldr.zip'
)

DEFAULT_LANG = os.environ.get(
    'TLDR_LANGUAGE',
    os.environ.get('LANG', None)
).split('_')[0]

if DEFAULT_LANG == 'C':
    DEFAULT_LANG = None

USE_CACHE = int(os.environ.get('TLDR_CACHE_ENABLED', '1')) > 0
MAX_CACHE_AGE = int(os.environ.get('TLDR_CACHE_MAX_AGE', 24))

URLOPEN_CONTEXT = None
if int(os.environ.get('TLDR_ALLOW_INSECURE', '0')) == 1:
    URLOPEN_CONTEXT = ssl.create_default_context()
    URLOPEN_CONTEXT.check_hostname = False
    URLOPEN_CONTEXT.verify_mode = ssl.CERT_NONE

OS_DIRECTORIES = {
    "linux": "linux",
    "darwin": "osx",
    "sunos": "sunos",
    "win32": "windows"
}


def get_cache_dir():
    if not os.environ.get('XDG_CACHE_HOME', False):
        if not os.environ.get('HOME', False):
            return os.path.join(os.path.expanduser("~"), ".cache", "tldr")
        return os.path.join(os.environ.get('HOME'), '.cache', 'tldr')
    return os.path.join(os.environ.get('XDG_CACHE_HOME'), 'tldr')


def get_cache_file_path(command, platform, language):
    pages_dir = "pages"
    if language and language != 'en':
        pages_dir += "." + language
    return os.path.join(get_cache_dir(), pages_dir, platform, command) + ".md"


def load_page_from_cache(command, platform, language):
    try:
        with open(get_cache_file_path(
            command,
            platform,
            language), 'rb'
        ) as cache_file:
            cache_file_contents = cache_file.read()
        return cache_file_contents
    except Exception:
        pass


def store_page_to_cache(page, command, platform, language):
    try:
        cache_file_path = get_cache_file_path(command, platform, language)
        os.makedirs(os.path.dirname(cache_file_path), exist_ok=True)
        with open(cache_file_path, "wb") as cache_file:
            cache_file.write(page)
    except Exception:
        pass


def have_recent_cache(command, platform, language):
    try:
        cache_file_path = get_cache_file_path(command, platform, language)
        last_modified = datetime.fromtimestamp(os.path.getmtime(cache_file_path))
        hours_passed = (datetime.now() - last_modified).total_seconds() / 3600
        return hours_passed <= MAX_CACHE_AGE
    except Exception:
        return False


def get_page_url(command, platform, remote, language):
    if remote is None:
        remote = PAGES_SOURCE_LOCATION

    if language is None or language == 'en':
        language = ''
    else:
        language = '.' + language

    return remote + language + "/" + platform + "/" + quote(command) + ".md"


def get_page_for_platform(command, platform, remote, language):
    data_downloaded = False
    if USE_CACHE and have_recent_cache(command, platform, language):
        data = load_page_from_cache(command, platform, language)
    else:
        page_url = get_page_url(command, platform, remote, language)
        try:
            data = urlopen(
                Request(page_url, headers=REQUEST_HEADERS),
                context=URLOPEN_CONTEXT
            ).read()
            data_downloaded = True
        except Exception:
            data = load_page_from_cache(command, platform, language)
            if data is None:
                raise
    if data_downloaded:
        store_page_to_cache(data, command, platform, language)
    return data.splitlines()


def update_page_for_platform(command, platform, remote, language):
    page_url = get_page_url(platform, command, remote, language)
    data = urlopen(
        Request(page_url, headers=REQUEST_HEADERS),
        context=URLOPEN_CONTEXT
    ).read()
    store_page_to_cache(data, command, platform, language)


def get_platform():
    for key in OS_DIRECTORIES:
        if sys.platform.startswith(key):
            return OS_DIRECTORIES[key]


def get_platform_list():
    platforms = ['common'] + list(OS_DIRECTORIES.values())
    current_platform = get_platform()
    platforms.remove(current_platform)
    platforms.insert(0, current_platform)
    return platforms


def get_language_list():
    languages = os.environ.get('LANGUAGES', '').split(':')
    languages = list(map(
        lambda x: x.split('_')[0],
        filter(lambda x: x != 'C', languages)
    ))
    if DEFAULT_LANG is not None:
        try:
            languages.remove(DEFAULT_LANG)
        except ValueError:
            pass
        languages.insert(0, DEFAULT_LANG)
    else:
        languages.append('en')
    return languages


def get_page(command, remote=None, platforms=None, languages=None):
    if platforms is None:
        platforms = get_platform_list()
    if languages is None:
        languages = get_language_list()
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

COMMAND_SPLIT_REGEX = re.compile(r'(?P<param>{{.+?}})')
PARAM_REGEX = re.compile(r'(?:{{)(?P<param>.+?)(?:}})')


def colors_of(key):
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


def output(page):
    # Need a better fancy method?
    if page is not None:
        print()
        for line in page:
            line = line.rstrip().decode('utf-8')
            if len(line) == 0:
                continue
            elif line[0] == '#':
                line = ' ' * LEADING_SPACES_NUM + \
                    colored(line.replace('# ', ''), *colors_of('name')) + '\n'
                sys.stdout.buffer.write(line.encode('utf-8'))
            elif line[0] == '>':
                line = ' ' * (LEADING_SPACES_NUM - 1) + \
                    colored(
                        line.replace('>', '').replace('<', ''),
                        *colors_of('description')
                    )
                sys.stdout.buffer.write(line.encode('utf-8'))
            elif line[0] == '-':
                line = '\n' + ' ' * LEADING_SPACES_NUM + \
                    colored(line, *colors_of('example'))
                sys.stdout.buffer.write(line.encode('utf-8'))
            elif line[0] == '`':
                line = line[1:-1]  # need to actually parse ``
                elements = [' ' * 2 * LEADING_SPACES_NUM]
                for item in COMMAND_SPLIT_REGEX.split(line):
                    item, replaced = PARAM_REGEX.subn(
                        lambda x: colored(
                            x.group('param'), *colors_of('parameter')),
                        item)
                    if not replaced:
                        item = colored(item, *colors_of('command'))
                    elements.append(item)
                sys.stdout.buffer.write(''.join(elements).encode('utf-8'))
            print()
        print()


def update_cache(language=None):
    if language is None:
        language = DEFAULT_LANG if DEFAULT_LANG is not None else 'en'
    elif isinstance(language, list):
        language = language[0]
    try:
        pages_dir = "pages"
        if language and language != 'en':
            pages_dir += "." + language
        req = urlopen(Request(
            DOWNLOAD_CACHE_LOCATION,
            headers=REQUEST_HEADERS
        ), context=URLOPEN_CONTEXT)
        zipfile = ZipFile(BytesIO(req.read()))
        pattern = re.compile(r"{}/(.+)/(.+)\.md".format(pages_dir))
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
        print("Updated cache for {:d} entries".format(cached))
    except Exception:
        sys.exit("Error: Unable to update cache from " + DOWNLOAD_CACHE_LOCATION)


def main():
    parser = ArgumentParser(
        prog="tldr",
        usage="tldr [-u] [-p PLATFORM] [-s SOURCE] [-c] [-r] [-L LANGUAGE] " +
        "command",
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

    parser.add_argument('-u', '--update_cache',
                        action='store_true',
                        help="Update the local cache of pages and exit")

    parser.add_argument(
        '-p', '--platform',
        nargs=1,
        default=None,
        type=str,
        choices=['linux', 'osx', 'sunos', 'windows', 'common'],
        metavar='PLATFORM',
        help="Override the operating system [linux, osx, sunos, windows, common]"
    )

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

    parser.add_argument(
        'command', type=str, nargs='*', help="command to lookup"
    )

    options = parser.parse_args()

    colorama.init(strip=options.color)

    if options.update_cache:
        update_cache(language=options.language)
        return
    elif len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if options.render:
        for command in options.command:
            if os.path.exists(command):
                with open(command, encoding='utf-8') as open_file:
                    output(open_file.read().encode('utf-8').splitlines())
    else:
        try:
            command = '-'.join(options.command)
            result = get_page(
                command,
                options.source,
                options.platform,
                options.language
            )
            if not result:
                print((
                    "`{cmd}` documentation is not available. "
                    "Consider contributing Pull Request to "
                    "https://github.com/tldr-pages/tldr"
                ).format(cmd=command), file=sys.stderr)
            else:
                output(result)
        except URLError as e:
            sys.exit("Error fetching from tldr: {}".format(e))


def cli():
    try:
        main()
    except KeyboardInterrupt:
        print("\nExited on keyboard interrupt.")


if __name__ == "__main__":
    cli()
