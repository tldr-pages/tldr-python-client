import sys
from setuptools import setup

setup_requires = ['setuptools_scm']
if sys.argv[-1] in ('sdist', 'bdist_wheel'):
    setup_requires.append('setuptools-markdown')

setup(
    name='tldr',
    author='Felix Yan',
    author_email='felixonmars@gmail.com',
    url='https://github.com/tldr-pages/tldr-python-client',
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
    use_scm_version=True,
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
