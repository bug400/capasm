from setuptools import setup, find_packages  # Always prefer setuptools over distutils
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='capasm',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='1.0.1',

    description='Assembler for the HP capricorn CPU',
    long_description=long_description,

    # Author details
    author='Joachim Siebold',
    author_email='bug400@gmx.de',

    # Choose your license
    license='GPL2',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: HP Calculator enthusiasts',
        'Topic :: Software Development :: Assemblers',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],

    # What does your project relate to?
    keywords='HP-75 HP-85',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['misc', 'debian', 'tests*']),
    entry_points={
       'console_scripts': [ 'capasm= capasm:capasm',
                            'ncas= capasm:ncas',
                            'caplex= capasm:caplex',
                            'capglo= capasm:capglo',
                            'caprom= capasm:caprom',
                            'capconv= capasm:capconv',
                            'caplif= capasm:caplif' ] ,
    }
)
