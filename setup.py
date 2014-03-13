from setuptools import setup, Extension
import distutils.core
import sys
import os

setup(
        name = 'tldr',
        version = "0.1.1",
        author = 'Felix Yan',
        author_email = 'felixonmars@gmail.com',
        url = 'https://github.com/felixonmars/tldr-python-client',
        description = 'command line client for tldr',
        license = 'MIT',
        py_modules = ['tldr'],
        scripts=['tldr.py'],
        install_requires = ['six', 'termcolor'],
        entry_points = { 'console_scripts': [ 'tldr = tldr:main' ] },
        classifiers = [
                "Development Status :: 4 - Beta",
                "License :: OSI Approved :: MIT License",
                "Environment :: Console",
                "Intended Audience :: End Users/Desktop",
                "Natural Language :: English",
                "Operating System :: POSIX :: Linux",
                "Operating System :: MacOS :: MacOS X",
                "Operating System :: POSIX :: SunOS/Solaris",
                "Programming Language :: Python :: 2.7",
                "Programming Language :: Python :: 3.3",
                "Topic :: Utilities",
                "Topic :: System"
        ]
)
