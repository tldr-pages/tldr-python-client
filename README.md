# tldr-python-client

[![PyPI Release](https://img.shields.io/pypi/v/tldr.svg)](https://pypi.python.org/pypi/tldr)
[![Build Status](https://travis-ci.org/tldr-pages/tldr-python-client.svg?branch=master)](https://travis-ci.org/tldr-pages/tldr-python-client)

A `Python` command line client for [tldr](https://github.com/tldr-pages/tldr).

![tldr screenshot](http://raw.github.com/tldr-pages/tldr/master/images/screenshot.png)

## Installation

### from PyPI

    pip install tldr

### from Arch Linux repository

    sudo pacman -S tldr

### from Fedora packages repository

    sudo dnf install tldr

## Usage

    usage: tldr [-u] [-p PLATFORM] [-s SOURCE] [-c] [-r] [-L LANGUAGE] command

    Python command line client for tldr

    optional arguments:
    -h, --help            show this help message and exit
    -v, --version         show program's version number and exit
    -u, --update_cache    Update the local cache of pages and exit
    -p PLATFORM, --platform PLATFORM
                            Override the operating system [linux, osx, sunos,
                            windows, common]
    -s SOURCE, --source SOURCE
                            Override the default page source
    -c, --color           Override color stripping
    -r, --render          Render local markdown files
    -L LANGUAGE, --language LANGUAGE
                            Override the default language

## Configuration

You can configure the behavior and output of the `tldr` client by setting environment variables. For example, in the `.bashrc` file:

    export TLDR_COLOR_NAME="cyan"
    export TLDR_COLOR_DESCRIPTION="white"
    export TLDR_COLOR_EXAMPLE="green"
    export TLDR_COLOR_COMMAND="red"
    export TLDR_COLOR_PARAMETER="white"
    export TLDR_CACHE_ENABLED=1
    export TLDR_CACHE_MAX_AGE=720
    export TLDR_PAGES_SOURCE_LOCATION="https://raw.githubusercontent.com/tldr-pages/tldr/master/pages"
    export TLDR_DOWNLOAD_CACHE_LOCATION="https://tldr-pages.github.io/assets/tldr.zip"
    export TLDR_LANGUAGE="en"

### Cache

Cache is downloaded from `TLDR_DOWNLOAD_CACHE_LOCATION` (defaults to the one described in [the client specification](https://github.com/tldr-pages/tldr/blob/master/CLIENT-SPECIFICATION.md#caching)), unzipped and extracted into the [local cache directory](#cache-location). Pages are loaded directly from `TLDR_PAGES_SOURCE_LOCATION` if `tldr <command>` is used.

* `TLDR_CACHE_ENABLED` (default is `1`):
    * If set to `1`, the client will first try to load from cache, and fall back to fetching from the internet if the cache doesn't exist or is too old.
    * If set to `0`, the client will fetch from the internet, and fall back to the cache if the page cannot be fetched from the internet.
* `TLDR_CACHE_MAX_AGE` (default is `24`): maximum age of the cache in hours to be considered as valid when `TLDR_CACHE_ENABLED` is set to `1`.

#### Cache location

In order of precedence:
* `$XDG_CACHE_HOME/tldr`
* `$HOME/.cache/tldr`
* `~/.cache/tldr`

If you are experiencing issues with *tldr*, consider deleting the cache files before trying other measures.

### SSL Inspection

For networks that sit behind a proxy, it may be necessary to disable SSL verification for the client to function. Setting the following:

* `TLDR_ALLOW_INSECURE=1` 

will disable SSL certificate inspection. This __should be avoided__ unless absolutely necessary.

### Colors

Values of the `TLDR_COLOR_x` variables may consist of three parts:
* Font color: `blue, green, yellow, cyan, magenta, white, grey, red`
* Background color: `on_blue, on_cyan, on_magenta, on_white, on_grey, on_yellow, on_red, on_green`
* Additional effects, which depends on platform: `reverse, blink, dark, concealed, underline, bold`

You may specify as many additional effects as you want, while only one of font and background color.

Any of the values of above may be omitted. For example, you can do similar things as the following:
* `TLDR_COLOR_NAME=""` use default system font color with default background color without any effects
* `TLDR_COLOR_DESCRIPTION="white"` for white text on default system background color without any effects
* `TLDR_COLOR_NAME="cyan dark"` for dark cyan text on default system background color
* `TLDR_COLOR_NAME="on_red"` for default system font color on red background color
* `TLDR_COLOR_PARAMETER="red on_yellow underline"` for underlined red text on yellow background
* `TLDR_COLOR_NAME="bold underline"` for default system font and background colors with underline and bolded effects

### Language 

The language that tldr will use is dependent on a number of factors. If you specify a language via the
`--language` flag, tldr will attempt to use that language and only that language. Otherwise, it will
default to language set using either `TLDR_LANGUAGE` before falling back to `LANG` (ignoring the value `C`).
If neither are set, then tldr will always attempt to get the `en` page. Finally, if `LANGUAGES` is set, it uses
this as the priority list to try languages in, with the exception that it will attempt `TLDR_LANGUAGE` and `LANG`
first, and if neither are set, will use `en` last (assuming it does not already appear somewhere in `LANGUAGES`).
All language values should be set to a value that follows [RFC 1766](https://tools.ietf.org/html/rfc1766.html),
with the special exception of `C` which is ignored.

### Remote source

If you wish to use your own instance of the tldr pages instead of the default repository, you
can either use the `--source` flag when using tldr or by specifying the following environment variables:

* `TLDR_PAGES_SOURCE_LOCATION` to control where to get individual pages from
  * defaults to `https://raw.githubusercontent.com/tldr-pages/tldr/master/pages`
  * it can also point to local directory using `file:///path/to/directory`
* `TLDR_DOWNLOAD_CACHE_LOCATION` to control where to pull a zip of all pages from
  * defaults to `https://tldr-pages.github.io/assets/tldr.zip`
