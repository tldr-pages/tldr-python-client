#!/usr/bin/env python
from __future__ import unicode_literals, print_function
import sys
import os
from argparse import ArgumentParser
from termcolor import colored, cprint
from six.moves.urllib.parse import quote
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError
from six.moves import map

## get terminal size
rows, columns = map(int, os.popen('stty size', 'r').read().split())

remote = "http://raw.github.com/rprieto/tldr/master/pages"

os_directories = {
    "linux": "linux",
    "darwin": "osx",
    "sunos": "sunos",
}

def get_page_for_platform(command, platform):
    data = urlopen(remote + "/" + platform + "/" + quote(command) + ".md")
    return data

def get_platform():
    for key in os_directories:
        if sys.platform.startswith(key):
            return os_directories[key]

    raise NotImplementedError(sys.platform, "not supported yet")

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
          "Consider contributing Pull Request to https://github.com/rprieto/tldr")

def output(page):
    # Need a fancy method
    if page is not None:
        print(page)

if __name__ == "__main__":
    parser = ArgumentParser(description="Python command line client for tldr")

    parser.add_argument('-o', '--os',
                        nargs=1,
                        default=None,
                        help="Override the operating system [linux, osx, sunos]")

    parser.add_argument('command', nargs='+', help=
                        "command to lookup")

    options = parser.parse_args()

    for command in options.command:
        if options.os is not None:
            output(get_page(command, options.os))

        else:
            output(get_page(command))
