import sys
from setuptools import setup

if sys.argv[-1] in ('sdist', 'bdist_wheel'):
    setup_requires = ['setuptools-markdown']
else:
    setup_requires = []

setup(
    name='tldr',
    version="0.1.3.1",
    author='Felix Yan',
    author_email='felixonmars@gmail.com',
    url='https://github.com/felixonmars/tldr-python-client',
    description='command line client for tldr',
    long_description_markdown_filename='README.md',
    license='MIT',
    py_modules=['tldr'],
    scripts=['tldr.py'],
    install_requires=['six', 'termcolor', 'colorama'],
    tests_require=[
        'pytest-runner',
    ],
    setup_requires=setup_requires,
    entry_points={
        'console_scripts': ['tldr = tldr:main']
    },
    classifiers=[
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
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Topic :: Utilities",
        "Topic :: System"
    ]
)
