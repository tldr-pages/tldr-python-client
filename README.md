# tldr-python-client

[![PyPI Release](https://img.shields.io/pypi/v/tldr.svg)](https://pypi.python.org/pypi/tldr)
[![Build Status](https://travis-ci.org/tldr-pages/tldr-python-client.svg)](https://travis-ci.org/tldr-pages/tldr-python-client)

A `Python` command line client for [tldr](https://github.com/tldr-pages/tldr).

![tldr screenshot](http://raw.github.com/tldr-pages/tldr/master/screenshot.png)

## Installation

    $ pip install tldr

## Usage

* `tldr <command>`

## Configuration
You can configure output of `tldr` client through setting an environment variables. For example, in `.bashrc` file:

    export TLDR_COLOR_BLANK="white"
    export TLDR_COLOR_NAME="cyan"
    export TLDR_COLOR_DESCRIPTION="white"
    export TLDR_COLOR_EXAMPLE="green"
    export TLDR_COLOR_COMMAND="red"
    export TLDR_COLOR_PARAMETER="white"
    
Values of these variables may consist of three parts: 
* Font color, *required*: `blue, green, yellow, cyan, magenta, white, grey, red`
* Background color: `on_blue, on_cyan, on_magenta, on_white, on_grey, on_yellow, on_red, on_green`
* Additional effects, which depends on platform: `reverse, blink, dark, concealed, underline, bold`

Values of background color and additional effect may be omitted:
* `TLDR_COLOR_DESCRIPTION="white"` for white text on default system background color without any effects
* `TLDR_COLOR_NAME="cyan dark"` for dark cyan text on default system background color 
* `TLDR_COLOR_PARAMETER="red on_yellow underline"` for underlined red text on yellow background
