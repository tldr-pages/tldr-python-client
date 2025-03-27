from pathlib import Path
import re
from setuptools import setup

setup_dir = Path(__file__).resolve().parent
version = re.search(
    r'__version__ = "(.*)"',
    Path(setup_dir, 'tldr.py').open().read()
)
if version is None:
    raise SystemExit("Could not determine version to use")
version = version.group(1)

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='tldr',
    author='Felix Yan and tldr-pages contributors',
    url='https://github.com/tldr-pages/tldr-python-client',
    description='command line client for tldr',
    long_description=Path(setup_dir, 'README.md').open().read(),
    long_description_content_type='text/markdown',
    license='MIT',
    py_modules=['tldr'],
    entry_points={
        "console_scripts": [
            "tldr = tldr:cli"
        ]
    },
    data_files=[('share/man/man1', ['docs/man/tldr.1'])],
    install_requires=required,
    tests_require=[
        'pytest',
        'pytest-runner',
    ],
    version=version,
    python_requires='~=3.8',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Operating System :: POSIX :: SunOS/Solaris",
        "Operating System :: POSIX :: BSD :: FreeBSD",
        "Operating System :: POSIX :: BSD :: NetBSD",
        "Operating System :: POSIX :: BSD :: OpenBSD",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Utilities",
        "Topic :: System"
    ]
)
