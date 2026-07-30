#!/usr/bin/env python
from setuptools import setup

import versioneer

DISTNAME = 'pyfolio'
DESCRIPTION = ("pyfolio is a Python library for performance "
               "and risk analysis of financial portfolios")
LONG_DESCRIPTION = """pyfolio is a Python library for performance and risk
analysis of financial portfolios developed by `Quantopian Inc`_. It works
well with the `Zipline`_ open source backtesting library.

At the core of pyfolio is a so-called tear sheet that consists of
various individual plots that provide a comprehensive performance
overview of a portfolio.

.. _Quantopian Inc: https://www.quantopian.com
.. _Zipline: http://zipline.io
"""
MAINTAINER = 'Quantopian Inc'
MAINTAINER_EMAIL = 'opensource@quantopian.com'
AUTHOR = 'Quantopian Inc'
AUTHOR_EMAIL = 'opensource@quantopian.com'
URL = "https://github.com/quantopian/pyfolio"
LICENSE = "Apache License, Version 2.0"

classifiers = ['Development Status :: 4 - Beta',
               'Programming Language :: Python',
               'Programming Language :: Python :: 3',
               'Programming Language :: Python :: 3.9',
               'Programming Language :: Python :: 3.10',
               'Programming Language :: Python :: 3.11',
               'Programming Language :: Python :: 3.12',
               'License :: OSI Approved :: Apache Software License',
               'Intended Audience :: Science/Research',
               'Topic :: Scientific/Engineering',
               'Topic :: Scientific/Engineering :: Mathematics',
               'Operating System :: OS Independent']

install_reqs = [
    'ipython>=7.0.0',
    'matplotlib>=3.3.0',
    'numpy>=1.20.0',
    'pandas>=2.0.0',
    'pytz>=2014.10',
    'scipy>=1.5.0',
    'scikit-learn>=0.21.0',
    'seaborn>=0.11.0',
    'empyrical-reloaded>=0.5.7',
]

test_reqs = ['pytest>=6.0', 'parameterized>=0.8.0']

extras_reqs = {
    'test': test_reqs,
    'all': test_reqs
}

if __name__ == "__main__":
    setup(
        name=DISTNAME,
        cmdclass=versioneer.get_cmdclass(),
        version=versioneer.get_version(),
        maintainer=MAINTAINER,
        maintainer_email=MAINTAINER_EMAIL,
        description=DESCRIPTION,
        license=LICENSE,
        url=URL,
        long_description=LONG_DESCRIPTION,
        packages=['pyfolio', 'pyfolio.tests'],
        package_data={'pyfolio': ['data/*.*']},
        classifiers=classifiers,
        install_requires=install_reqs,
        extras_require=extras_reqs,
        python_requires='>=3.9',
    )
