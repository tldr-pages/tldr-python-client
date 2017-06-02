#!/usr/bin/env python
from __future__ import unicode_literals, print_function, division
import sys
import os
import errno
import subprocess
import re
from argparse import ArgumentParser

from datetime import datetime
from termcolor import colored, cprint
from six.moves.urllib.parse import quote
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError
from six.moves import map
# Required for Windows
import colorama
colorama.init()

USE_CACHE = int(os.environ.get('TLDR_CACHE_ENABLED', '1')) > 0
MAX_CACHE_AGE = int(os.environ.get('TLDR_CACHE_MAX_AGE', 24))

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

remote = "http://raw.github.com/tldr-pages/tldr/master/pages"

os_directories = {
    "linux": "linux",
    "darwin": "osx",
    "sunos": "sunos"
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


def get_page_for_platform(command, platform):
    data_downloaded = False
    if have_recent_cache(command, platform):
        data = load_page_from_cache(command, platform)
    else:
        page_url = remote + "/" + platform + "/" + quote(command) + ".md"
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


def download_and_store_page_for_platform(command, platform):
    page_url = remote + "/" + platform + "/" + quote(command) + ".md"
    data = urlopen(page_url).read()
    store_page_to_cache(data, command, platform)


def get_platform():
    for key in os_directories:
        if sys.platform.startswith(key):
            return os_directories[key]


def get_page(command, platform=None):
    if platform is None:
        platform = ["common", get_platform()]

    for _platform in platform:
        try:
            return get_page_for_platform(command, _platform)
        except HTTPError as e:
            if e.code != 404:
                raise

    print(command + " documentation is not available\n"
          "Consider contributing Pull Request to https://github.com/tldr-pages/tldr")


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


def update_cache():
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
            download_and_store_page_for_platform(command, platform)
            print('Updated cache for %s (%s)' % (command, platform))
        except Exception:
            print('Error: Unable to get %s (%s)' % (command, platform))



def main():
    parser = ArgumentParser(description="Python command line client for tldr")

    parser.add_argument('-u', '--update_cache',
                        action='store_true',
                        help="Update the cached commands")

    parser.add_argument('-o', '--os',
                        nargs=1,
                        default=None,
                        type=str,
                        choices=['linux', 'osx', 'sunos'],
                        help="Override the operating system [linux, osx, sunos]")

    options, other_options = parser.parse_known_args()

    if options.update_cache:
        update_cache()
        return

    parser.add_argument(
        'command', type=str, nargs='+', help="command to lookup")

    options = parser.parse_args(other_options)

    for command in options.command:
        try:
            if options.os is not None:
                output(get_page(command, options.os))
            else:
                output(get_page(command))
        except Exception:
            print("No internet connection detected. Please reconnect and try again.")


if __name__ == "__main__":
    main()
