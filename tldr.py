#!/usr/bin/env python
from __future__ import unicode_literals, print_function, division
import sys
import os
import errno
import subprocess
import re
from argparse import ArgumentParser
from zipfile import ZipFile

from datetime import datetime
from termcolor import colored, cprint
from six import BytesIO
from six.moves.urllib.parse import quote
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError
from six.moves import map
# Required for Windows
import colorama

DEFAULT_REMOTE = "https://raw.githubusercontent.com/tldr-pages/tldr/master/pages"
USE_CACHE = int(os.environ.get('TLDR_CACHE_ENABLED', '1')) > 0
MAX_CACHE_AGE = int(os.environ.get('TLDR_CACHE_MAX_AGE', 24))
DOWNLOAD_CACHE_LOCATION = 'https://tldr-pages.github.io/assets/tldr.zip'

COMMAND_FILE_REGEX = re.compile(r'(?P<command>^.+?)_(?P<platform>.+?)\.md$')


def get_terminal_size():
    def get_terminal_size_windows():
        try:
            from ctypes import windll, create_string_buffer
            import struct
            # stdin handle is -10
            # stdout handle is -11
            # stderr handle is -12
            h = windll.kernel32.GetStdHandle(-12)
            csbi = create_string_buffer(22)
            res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
            if res:
                (bufx, bufy, curx, cury, wattr,
                 left, top, right, bottom,
                 maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
                sizex = right - left + 1
                sizey = bottom - top + 1
                return sizex, sizey
        except:
            pass

    def get_terminal_size_stty():
        try:
            return map(int, subprocess.check_output(['stty', 'size']).split())
        except:
            pass

    def get_terminal_size_tput():
        try:
            return map(int, [subprocess.check_output(['tput', 'lines']), subprocess.check_output(['tput', 'rows'])])
        except:
            pass

    return get_terminal_size_windows() or get_terminal_size_stty() or get_terminal_size_tput() or (25, 80)


# get terminal size
rows, columns = get_terminal_size()

os_directories = {
    "linux": "linux",
    "darwin": "osx",
    "sunos": "sunos",
    "win32": "windows",
}


def get_cache_dir():
    if not os.environ.get('XDG_CACHE_HOME', False):
        if not os.environ.get('HOME', False):
            return os.path.join(os.path.expanduser("~"), ".cache", "tldr")
        return os.path.join(os.environ.get('HOME'), '.cache', 'tldr')
    return os.path.join(os.environ.get('XDG_CACHE_HOME'), 'tldr')


def get_cache_file_path(command, platform):
    cache_file_name = command + "_" + platform + ".md"
    cache_file_path = os.path.join(get_cache_dir(), cache_file_name)
    return cache_file_path


def load_page_from_cache(command, platform):
    try:
        with open(get_cache_file_path(command, platform), 'rb') as cache_file:
            cache_file_contents = cache_file.read()
        return cache_file_contents
    except Exception:
        pass


def store_page_to_cache(page, command, platform):
    def mkdir_p(path):
        """
        Create all the intermediate directories in a path.
        Similar to the `mkdir -p` command.
        """
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    try:
        cache_file_path = get_cache_file_path(command, platform)
        mkdir_p(os.path.dirname(cache_file_path))
        with open(cache_file_path, "wb") as cache_file:
            cache_file.write(page)
    except Exception:
        pass


def have_recent_cache(command, platform):
    try:
        cache_file_path = get_cache_file_path(command, platform)
        last_modified = datetime.fromtimestamp(os.path.getmtime(cache_file_path))
        hours_passed = (datetime.now() - last_modified).total_seconds() / 3600
        return hours_passed <= MAX_CACHE_AGE
    except Exception:
        return False


def get_page_url(platform, command, remote=None):
    if remote is None:
        remote = DEFAULT_REMOTE
    return remote + "/" + platform + "/" + quote(command) + ".md"


def get_page_for_platform(command, platform, remote=None):
    data_downloaded = False
    if USE_CACHE and have_recent_cache(command, platform):
        data = load_page_from_cache(command, platform)
    else:
        page_url = get_page_url(platform, command, remote)
        try:
            data = urlopen(page_url).read()
            data_downloaded = True
        except Exception:
            data = load_page_from_cache(command, platform)
            if data is None:
                raise
    if data_downloaded:
        store_page_to_cache(data, command, platform)
    return data.splitlines()


def download_and_store_page_for_platform(command, platform, remote=None):
    page_url = get_page_url(platform, command, remote)
    data = urlopen(page_url).read()
    store_page_to_cache(data, command, platform)


def get_platform():
    for key in os_directories:
        if sys.platform.startswith(key):
            return os_directories[key]


def get_page(command, remote=None, platform=None):
    if platform is None:
        platform = [get_platform(), "common"]
    for _platform in platform:
        if _platform is None:
            continue
        try:
            return get_page_for_platform(command, _platform, remote=remote)
        except HTTPError as e:
            if e.code != 404:
                raise

    return False


DEFAULT_COLORS = {
    'blank': 'white',
    'name': 'white bold',
    'description': 'white',
    'example': 'green',
    'command': 'red',
    'parameter': 'white',
}

LEADING_SPACES_NUM = 2

command_splitter = re.compile(r'(?P<param>{{.+?}})')
param_regex = re.compile(r'(?:{{)(?P<param>.+?)(?:}})')


def colors_of(key):
    env_key = 'TLDR_COLOR_%s' % key.upper()
    values = os.environ.get(env_key, '').strip() or DEFAULT_COLORS[key]
    values = values.split()
    return (
        values[0] if len(values) > 0 else None,
        values[1] if len(values) > 1 and values[1].startswith('on_') else None,
        values[2:] if len(values) > 1 and values[1].startswith('on_') else values[1:],
    )


def output(page):
    # Need a better fancy method?
    if page is not None:
        for line in page:
            line = line.rstrip().decode('utf-8')
            if len(line) < 1:
                cprint(line.ljust(columns), *colors_of('blank'))
            elif line[0] == '#':
                cprint(line.ljust(columns), *colors_of('name'))
            elif line[0] == '>':
                line = ' ' + line[1:]
                cprint(line.ljust(columns), *colors_of('description'))
            elif line[0] == '-':
                cprint(line.ljust(columns), *colors_of('example'))
            elif line[0] == '`':
                line = line[1:-1]  # need to actually parse ``
                elements = [
                    colored(' ' * LEADING_SPACES_NUM, *colors_of('blank')), ]
                replaced_spaces = 0
                for item in command_splitter.split(line):
                    item, replaced = param_regex.subn(
                        lambda x: colored(
                            x.group('param'), *colors_of('parameter')),
                        item)
                    if not replaced:
                        item = colored(item, *colors_of('command'))
                    else:
                        # In replacement of {{}} from template pattern
                        replaced_spaces += 4
                    elements.append(item)
                # Manually adding painted in blank spaces
                elements.append(colored(' ' * (columns
                                               - len(line)
                                               - LEADING_SPACES_NUM
                                               + replaced_spaces), *colors_of('blank')))
                print(''.join(elements))
            else:
                cprint(line.ljust(columns), *colors_of('description'))
        # Need a cleaner way to pad three colored lines
        [cprint(''.ljust(columns), *colors_of('blank')) for i in range(3)]


def update_cache(remote=None):
    cache_path = get_cache_dir()
    if not os.path.exists(cache_path):
        return
    files = [file_name for file_name in os.listdir(cache_path)
             if os.path.isfile(os.path.join(cache_path, file_name)) and
             COMMAND_FILE_REGEX.match(file_name)]
    for file_name in files:
        match = COMMAND_FILE_REGEX.match(file_name)
        command = match.group('command')
        platform = match.group('platform')
        try:
            download_and_store_page_for_platform(command, platform, remote=remote)
            print('Updated cache for %s (%s) from %s' % (command, platform, remote))
        except Exception:
            sys.exit('Error: Unable to get %s (%s) from %s' % (command, platform, remote))


def download_cache():
    cache_path = get_cache_dir()
    if not os.path.exists(cache_path):
        return
    try:
        req = urlopen(DOWNLOAD_CACHE_LOCATION)
        zipfile = ZipFile(BytesIO(req.read()))
        pattern = re.compile(r'pages/(.+)/(.+)\.md')
        cached = 0
        for entry in zipfile.namelist():
            match = pattern.match(entry)
            if match:
                store_page_to_cache(zipfile.read(entry), match.group(2), match.group(1))
                cached += 1
        print("Updated cache for {:d} entries".format(cached))
    except Exception:
        sys.exit("Error: Unable to update cache from tldr site")


def main():
    parser = ArgumentParser(prog="tldr", description="Python command line client for tldr")

    parser.add_argument('-u', '--update_cache',
                        action='store_true',
                        help="Update the cached commands")

    parser.add_argument('--download_cache',
                        action='store_true',
                        help='Downloads and caches all tldr pages from tldr site')

    parser.add_argument('-p', '--platform',
                        nargs=1,
                        default=None,
                        type=str,
                        choices=['linux', 'osx', 'sunos', 'windows', 'common'],
                        metavar='PLATFORM',
                        help="Override the operating system [linux, osx, sunos, windows, common]")

    parser.add_argument('-s', '--source',
                        default=DEFAULT_REMOTE,
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

    options, rest = parser.parse_known_args()

    colorama.init(strip=options.color)

    if options.download_cache:
        download_cache()
        return

    if options.update_cache:
        update_cache(remote=options.source)
        return

    parser.add_argument(
        'command', type=str, nargs='+', help="command to lookup")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    rest = parser.parse_args(rest)

    if options.render:
        for command in rest.command:
            if os.path.exists(command):
                with open(command, encoding='utf-8') as open_file:
                    output(open_file.read().encode('utf-8').splitlines())
    else:
        try:
            result = get_page('-'.join(rest.command), platform=options.platform, remote=options.source)
            if not result:
                errors_found = False
                for command in rest.command:
                    result = get_page(command, platform=options.platform, remote=options.source)
                    if not result:
                        errors_found = True
                        print((
                            "`{cmd}` documentation is not available. "
                            "Consider contributing Pull Request to https://github.com/tldr-pages/tldr"
                        ).format(cmd=command), file=sys.stderr)
                    else:
                        output(result)
            else:
                output(result)
        except Exception:
            sys.exit("No internet connection detected. Please reconnect and try again.")

if __name__ == "__main__":
    main()
