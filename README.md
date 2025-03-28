# tldr-python-client

[![PyPI Release](https://img.shields.io/pypi/v/tldr.svg)](https://pypi.python.org/pypi/tldr)
[![Test](https://github.com/tldr-pages/tldr-python-client/actions/workflows/test.yml/badge.svg)](https://github.com/tldr-pages/tldr-python-client/actions/workflows/test.yml)
[![CodeQL](https://github.com/tldr-pages/tldr-python-client/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/tldr-pages/tldr-python-client/actions/workflows/github-code-scanning/codeql)
[![Snap Release](https://snapcraft.io/tldr/badge.svg)](https://snapcraft.io/tldr)

🐍 Official Python command-line client for [tldr pages](https://github.com/tldr-pages/tldr) 📚.

![Tldr Python client displaying the tar page](https://raw.github.com/tldr-pages/tldr-python-client/main/images/tldr-dark.png)

## Installation

<details open>
  <summary>Check Repology Packaging Status!</summary>
  <a href="https://repology.org/project/tldr-python-client/versions">
      <img src="https://repology.org/badge/vertical-allrepos/tldr-python-client.svg" alt="Packaging status">
  </a>
</details>

### from PyPI

```bash
pip install tldr
```

### from Arch Linux repository

```bash
sudo pacman -S tldr
```

### from Fedora packages repository

```bash
sudo dnf install tldr
```

### from Snap Store

```bash
sudo snap install tldr
```

## Usage

```bash
usage: tldr command [options]

Python command line client for tldr

positional arguments:
  command               command to lookup

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  --search "KEYWORDS"   Search for a specific command from a query
  -u, --update, --update_cache
                        Update the local cache of pages and exit
  -k, --clear-cache     Delete the local cache of pages and exit
  -p PLATFORM, --platform PLATFORM
                        Override the operating system [android, freebsd, linux, netbsd, openbsd, osx, sunos, windows, common]
  -l, --list            List all available commands for operating system
  -s SOURCE, --source SOURCE
                        Override the default page source
  -c, --color           Override color stripping
  -r, --render          Render local markdown files
  -L LANGUAGE, --language LANGUAGE
                        Override the default language
  -m, --markdown        Just print the plain page file.
  --short-options       Display shortform options over longform
  --long-options        Display longform options over shortform
  --print-completion {bash,zsh,tcsh}
                        print shell completion script
```

## Configuration

You can configure the behavior and output of the `tldr` client by setting environment variables. For example, in the `.bashrc` file:

```bash
export TLDR_COLOR_NAME="cyan"
export TLDR_COLOR_DESCRIPTION="white"
export TLDR_COLOR_EXAMPLE="green"
export TLDR_COLOR_COMMAND="red"
export TLDR_COLOR_PARAMETER="white"
export TLDR_LANGUAGE="es"
export TLDR_CACHE_ENABLED=1
export TLDR_CACHE_MAX_AGE=720
export TLDR_PAGES_SOURCE_LOCATION="https://raw.githubusercontent.com/tldr-pages/tldr/main/pages"
export TLDR_DOWNLOAD_CACHE_LOCATION="https://github.com/tldr-pages/tldr/releases/latest/download/tldr.zip"
export TLDR_OPTIONS=short
```

### Cache

Cache is downloaded from `TLDR_DOWNLOAD_CACHE_LOCATION` (defaults to the one described in [the client specification](https://github.com/tldr-pages/tldr/blob/main/CLIENT-SPECIFICATION.md#caching)), unzipped and extracted into the [local cache directory](#cache-location). Pages are loaded directly from `TLDR_PAGES_SOURCE_LOCATION` if `tldr <command>` is used.

- `TLDR_CACHE_ENABLED` (default is `1`):
  - If set to `1`, the client will first try to load from cache, and fall back to fetching from the internet if the cache doesn't exist or is too old.
  - If set to `0`, the client will fetch from the internet, and fall back to the cache if the page cannot be fetched from the internet.
- `TLDR_CACHE_MAX_AGE` (default is `168` hours, which is equivalent to a week): maximum age of the cache in hours to be considered as valid when `TLDR_CACHE_ENABLED` is set to `1`.

#### Cache location

In order of precedence:

- `$XDG_CACHE_HOME/tldr`
- `$HOME/.cache/tldr`
- `~/.cache/tldr`

If you are experiencing issues with *tldr*, consider deleting the cache files before trying other measures:

```bash
tldr --clear-cache
```

#### Autocomplete

[`shtab`](https://pypi.org/project/shtab) is required for autocompletion using the `--print-completion` argument.

```bash
# bash
tldr --print-completion bash | sudo tee "$BASH_COMPLETION_COMPAT_DIR"/tldr

# zsh (it is recommended to check where zsh/site-functions directory is located)
## for macOS:
tldr --print-completion zsh | sudo tee /usr/local/share/zsh/site-functions/_tldr
## for Linux:
tldr --print-completion zsh | sudo tee /usr/share/zsh/site-functions/_tldr
```

See the `shtab` [docs](https://pypi.org/project/shtab/#usage) for other installation methods and
supported shells.

For autocomplete in [`fish`](https://fishshell.com/), while it is not supported in `shtab` yet,
please see [#183](https://github.com/tldr-pages/tldr-python-client/issues/183) for manually adding
an autocomplete for `tldr` for `fish`.

### SSL Inspection

For networks that sit behind a proxy, it may be necessary to disable SSL verification for the client to function. Setting the following:

- `TLDR_ALLOW_INSECURE=1`

will disable SSL certificate inspection. This __should be avoided__ unless absolutely necessary.

Alternatively, It is possible to use a different certificate store/bundle by setting:

- `TLDR_CERT=/path/to/certificates.crt`

### Colors

Values of the `TLDR_COLOR_x` variables may consist of three parts:

- Font color: `blue, green, yellow, cyan, magenta, white, grey, red`
- Background color: `on_blue, on_cyan, on_magenta, on_white, on_grey, on_yellow, on_red, on_green`
- Additional effects, which depend on the platform: `reverse, blink, dark, concealed, underline, bold`

You may specify as many additional effects as you want, while only one of font and background color.

Any of the values above may be omitted. For example, you can do similar things as the following:

- `TLDR_COLOR_NAME=""` use default system font color with default background color without any effects
- `TLDR_COLOR_DESCRIPTION="white"` for white text on default system background color without any effects
- `TLDR_COLOR_NAME="cyan dark"` for dark cyan text on default system background color
- `TLDR_COLOR_NAME="on_red"` for default system font color on the red background color
- `TLDR_COLOR_PARAMETER="red on_yellow underline"` for underlined red text on yellow background
- `TLDR_COLOR_NAME="bold underline"` for default system font and background colors with underline and bolded effects

### Language

The language that tldr will use is dependent on several factors. If you specify a language via the
`--language` flag, tldr will attempt to use that language and only that language. Otherwise, it will
try to use the language specified by `TLDR_LANGUAGE`. If it is not set, or the page does not exist in that language,
then tldr will use the
language set using `LANGUAGE` and `LANG` (ignoring the values `C` and `POSIX`).

If neither is set, then tldr will always attempt to get the `en` page. Finally, if `LANG` is set, it uses `LANGUAGE`, if set,
first, as the priority list to try languages in, followed by `LANG` if not included in `LANGUAGE`
and `en` as a fallback (assuming it does not already appear somewhere in `LANGUAGE` or `LANG`).

All language values should be set to a value that follows [RFC 1766](https://tools.ietf.org/html/rfc1766.html),
with the special exceptions of `C` and `POSIX` which are ignored.

### Remote source

If you wish to use your own instance of the tldr pages instead of the default repository, you
can either use the `--source` flag when using tldr or by specifying the following environment variables:

- `TLDR_PAGES_SOURCE_LOCATION` to control where to get individual pages from.
  - defaults to `https://raw.githubusercontent.com/tldr-pages/tldr/main/pages`.
  - it can also point to a local directory using `file:///path/to/directory`.
- `TLDR_DOWNLOAD_CACHE_LOCATION` to control where to pull a zip of all pages from.
  - defaults to `https://github.com/tldr-pages/tldr/releases/latest/download/tldr.zip`.

### Command options

Pages might contain `{{[*|*]}}` patterns to let the client decide whether to show shortform or longform versions of options. This can be configured with `TLDR_OPTIONS`, which accepts values `short`, `long` and `both`.
