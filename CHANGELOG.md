# Changelog

## 3.4.0 (03/28/2025)

### Breaking

* Drop support for EOL Python 3.8 version.

### Bugfixes

* Fix broken `--render` option (thanks [@acuteenvy](https://github.com/acuteenvy))
* Fix duplicate platform information shown in pages like `du`, `cd`, `w` (thanks [@sellisd](https://github.com/sellisd))
* Only install `colorama` dependency in Windows (thanks [@hukkin](https://github.com/hukkin))

### Features

* Add support for displaying pages with long/short option placeholders using `--long-options`/`--short-options` flags or [TLDR_OPTIONS variable](https://github.com/tldr-pages/tldr-python-client#command-options) (thanks [@Managor](https://github.com/Managor))
* Add `--clear-cache`/`-k` option to clear tldr's local cache (thanks [@patricedenis](https://github.com/patricedenis) and [@vitorhcl](https://github.com/vitorhcl))
* Add support to stylize text inside backticks when appearing in example descriptions (thanks [@kyluca](https://github.com/kyluca))
* Add support for specifying a certificate bundle with [TLDR_CERT variable](https://github.com/tldr-pages/tldr-python-client#ssl-inspection) (thanks [@jtcbrule](https://github.com/jtcbrule), [@CleanMachine1](https://github.com/CleanMachine1), and [@vitorhcl](https://github.com/vitorhcl))
* Package build for the project has been migrated from using `setup.py` (with `setuptools` backend) to `pyproject.toml` (with Hatch backend) (thanks [@kbdharun](https://github.com/kbdharun))
* Update package metadata in `pyproject.toml` (thanks [@kbdharun](https://github.com/kbdharun))
* Add trusted publisher support to securely publish `tldr` package to PyPI directly from the repository's confined environment (thanks [@kbdharun](https://github.com/kbdharun))
* Add support for [Client Specification v2.3](https://github.com/tldr-pages/tldr/releases/tag/v2.3)

## 3.3.0 (06/29/2024)

### Breaking

* Drop support for EOL versions Python 3.6 and Python 3.7.

### Bugfixes

* Return `str` instead of `list` when executing `tldr -l` (thanks [@uunnxx](https://github.com/uunnxx))
* Use pathlib instead of os.path (thanks [@vitorhcl](https://github.com/vitorhcl))
* Respect language settings when geting a list of commands (thanks [@frenzymadness](https://github.com/frenzymadness))
* Fix `--search` option (thanks [@CleanMachine1](https://github.com/CleanMachine1))

### Features

* Add support for BSD platform directories (thanks [@vitorhcl](https://github.com/vitorhcl))
* Add `--update` long option (thanks [@owenvoke](https://github.com/owenvoke))
* Add support for fetching individual translation archives for cache (thanks [@SaurabhDRao](https://github.com/SaurabhDRao))
* Add support to show message for other versions of the same page in other platforms (thanks [@Jaimepas77](https://github.com/Jaimepas77))
* Update `DOWNLOAD_CACHE_LOCATION` to use GitHub Releases (thanks [@vitorhcl](https://github.com/vitorhcl))
* Add `macos` alias for `osx` directory and update `--platform` option (thanks [@patricedenis](https://github.com/patricedenis))
* Add support for escaping placeholders for special pages (thanks [@kbdharun](https://github.com/kbdharun))
* Add support for Python 3.11 and Python 3.12 (thanks [@kbdharun](https://github.com/kbdharun))
* Add support for [Client Specification v2.2](https://github.com/tldr-pages/tldr/releases/tag/v2.2)

## 3.2.0 (05/09/2023)

### Bugfixes

* Fix forcing color through termcolor
* Change non-word regex to be POSIX compliant (thanks [@stevejbrown](https://github.com/stevejbrown))
* Update pages source to use the main branch
* Add a timeout to the URL requests (thanks [@Jaimepas77](https://github.com/Jaimepas77))

## 3.1.0 (02/16/2022)

### Features

* Add `--search` option to find tldr pages based on keywords (thanks [@gotlougit](https://github.com/gotlougit))
* Specify support for v1.5 of the [tldr client specification](https://github.com/tldr-pages/tldr/blob/main/CLIENT-SPECIFICATION.md)

### Bugfixes

* Command names are lowercased before searching for page
* Fix color printing for tokens that end with curly braces

## 3.0.0 (10/27/2021)

### Breaking

We have moved from [argcomplete](https://github.com/kislyuk/argcomplete) to [shtab](https://github.com/iterative/shtab) for
providing shell completions. This library is more efficient on doing tab completion, avoiding costly time it takes for the python
intrepreter to parse tldr to get options.

See [Readme#autocomplete](https://github.com/tldr-pages/tldr-python-client#autocomplete) for details on setting up shtab. Please
see the [argcomplete README](https://github.com/kislyuk/argcomplete) for details on where to look to remove its provided completions.

### Features

* __breaking__ Move to shtab for tab completion support (thanks [@casperdcl](https://github.com/casperdcl))
* Change default max cache age from 1 day to 7 days, can get prior behavior by setting the `TLDR_CACHE_MAX_AGE` environment variable
* Install manpage in pypi package
* Add option to print raw markdown (thanks [@dadav](https://github.com/dadav))
* Support Python 3.10

## 2.0.0 (07/19/2021)

### Features

* __breaking__ Drop support for Python 3.5 (thanks [@nebnola](https://github.com/nebnola))
* Allow overriding system language using `TLDR_LANGUAGE` environment variable (thanks [@nebnola](https://github.com/nebnola))

### Fixes

* Improve wording of missing page error message (thanks [@CleanMachine1](https://github.com/CleanMachine1))

## 1.2.1 (04/01/2021)

### Fixes

* Fallback to using linux as platform if no pages folder found for current platform

## 1.2.0 (01/31/2020)

### Features

* Get remote resource only after all cache failed ([#151](https://github.com/tldr-pages/tldr-python-client/pull/151)) (thanks @ramwin)

### Fixes

* Set `--help` usage line to match node client ([#149](https://github.com/tldr-pages/tldr-python-client/pull/149))

## 1.1.0 (10/17/2020)

### Features

* Add autocomplete and `--list` command (thanks [@wcheang](https://github.com/wcheang))
* Always fall back to English for LANG / LANGUAGE env vars (thanks [@columbarius](https://github.com/columbarius))

### Fixes

* Exit with code `1` when command not found (thanks [@samuel-w](https://github.com/samuel-w))
* Check that cache directory exists on platform before using it

## 1.0.0 (05/16/2020)

### Features

* __breaking__ Drop support for Python 2 and Python 3.4
* __breaking__ Rename environment variable `TLDR_REMOTE_SOURCE` to `TLDR_SOURCE`
* __breaking__ Remove ability to print out multiple pages at the same time
* __breaking__ Make `--update` act the same as `--download_cache`, remove ability to only update currently cached pages
* __breaking__ Remove `--download_cache` flag (redundant to `--update`)
* __breaking__ Remove printing of tldr page to console width, and remove any ability to paint blank lines (see [#98](https://github.com/tldr-pages/tldr-python-client/pull/98) for more info)
* Verify if colors specified via environment variables are valid, fallback to default if not
* Set `User-Agent` header for urlopen requests
* Allow specifying endpoints for pages and cache via environment variables
* Explicitly state support for Python 3.8
* Use default terminal colors instead of always white for printing text
* Catch KeyboardInterrupt exception to display appropriate message
* Add ability to disable SSL inspection
* Add `--version` flag to cli to print out cli version and supported client specification
* Move to using `long_description` and `long_description_content_type` to handle markdown README in setup.py
* Add support for handling pages in other languages
* Remove symlink script in-favor of entry_points again
* Narrow top-level catch-all exception to only catch urllib exceptions

### Fixes

* Handle using `file://` as remote source for pulling pages
* Improve handling of environment variable colors to not be order specific of options

### Chores

* Update LICENSE to LICENSE.md
* Move to GitHub actions from Travis-CI
* Use flake8 to lint codebase

## 0.5.0 (04/01/2019)

### Features

* Changed `--os` flag to `--platform` to conform to client specification
* Add windows as available platform to search for for `--platform` option
* Add `--render` flag to parse local markdown files
* Add `--download_cache` flag to pull down entire TLDR cache
* Explicitly state support for Python 3.7
* Print errors to `sys.stderr` and use non-zero exit code

### Fixes

* Use newer raw github path to fetch pages
* Detect windows as current platform from sys.platform

## 0.4.4 (06/03/2018)

### Fixes

* Fix using http to fetch pages in 0.4.3, use https again
* Fix the cli options always using their default values
* Fix typo in parameter name in function definition

## 0.4.3 (06/03/2018)

### Features

* Add `--source` option to control where to fetch page
* Add support for space separated commands, fallback to showing multiple pages if concatenated name does not exist
* Add `--color` option to toggle whether to strip colors or not.

## 0.4.2 (01/14/2018)

### Fixes

* Use https for fetching pages
* Use symlink over entry points for package installation

### Chores

* Add description of cache location to README

## 0.4.1 (11/29/2017)

### Fixes

* Add Python 3.6 to setup.py classifiers
* Check `USE_CACHE` before attempting to load from cache

## 0.4.0 (06/04/2017)

### Features

* Update default colors to match node client (remove blue default background color)
* Add top-level exception handling to catch all thrown exceptions and display generic network message
* Test against Python 3.6
* Add support for setting cache location using `XDG_CACHE_HOME` environment variable for cache location
* Move default cache location from `${HOME}/.tldr_cache` to `${HOME}/.cache/tldr` (if `XDG_CACHE_HOME` not set)

### Fixes

* Write and read from cache files using binary mode

## 0.3.0 (08/15/2016)

### Features

* Use cache to display page by default before attempting to fetch from network, depending on age
* Add configuration settings to control cache enabled and max page age before fetching via network
* Add `--update` flag to update all previously cached pages

### Chores

* Update README with information on color configuration
* Add pypi badge to README

## 0.2.0 (02/01/2016)

### Features

* Nest `get_terminal_size()` to prevent namespace pollution
* Add ability to cache fetched pages, which are used as fallback if there is network problems
* Add ability to omit background colors when printing
* Use `setuptools_scm` to determine version for client in setup.py

### Fixes

* Fix URL pointing to old location to client in setup.py

## 0.1.3.1 (01/06/2016)

### Features

* Use setuptools-markdown to parse markdown readme for pypi

### Fixes

* Add missing Python 3.4 and 3.5 classifiers to setup.py

## 0.1.3 (01/06/2016)

### Features

* Add support for parsing and painting user input parameters in tldr pages

### Build

* Create basic test suite
* Set-up Travis test pipeline for Python 2.7, 3.3+

## 0.1.2 (12/31/2015)

### Features

* Migrate to tldr-pages organization from rprieto
* Add ability to set display colors via environment variables
* Add basic README
* Replace `os.popen()` with equivalent functions from subprocess module
* Add support for client for Windows

## 0.1.1 (03/13/2014)

* Initial Release
