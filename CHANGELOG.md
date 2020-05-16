# Changelog

## 1.0.0 (05/16/2020)

### Features

* __breaking__ Drop support for Python 2 and Python 3.4
* __breaking__ Rename environment variable `TLDR_REMOTE_SOURCE` to `TLDR_SOURCE`
* __breaking__ Remove ability to print out multiple pages at the same time
* __breaking__ Make `--update` act the same as `--download_cache`, remove ability to only update currently cached pages
* __breaking__ Remove `--download_cache` flag (redundant to `--update`)
* __breaking__ Remove printing of tldr page to console width, and remove any ability to paint blank lines (see #98 for more info)
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
