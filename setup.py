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

setup(
    name='tldr',
    author='Felix Yan',
    author_email='felixonmars@gmail.com',
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
    install_requires=['termcolor', 'colorama'],
    tests_require=[
        'pytest',
        'pytest-runner',
    ],
    version=version,
    python_requires='~=3.5',
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: SunOS/Solaris",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Utilities",
        "Topic :: System"
    ]
)
