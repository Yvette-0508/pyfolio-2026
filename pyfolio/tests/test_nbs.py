#!/usr/bin/env python
"""
simple example script for running notebooks and reporting exceptions.
Each cell is submitted to the kernel, and checked for errors.
"""

import os
import glob

import pytest

import nbformat
from nbclient import NotebookClient

import pyfolio

# The bundled example notebooks predate the Quantopian shutdown and
# depend on zipline and data services that no longer exist, so only
# execute them when explicitly requested.
RUN_NBS = os.environ.get('PYFOLIO_TEST_NBS') == '1'


@pytest.mark.skipif(not RUN_NBS, reason='set PYFOLIO_TEST_NBS=1 to run '
                                        'the legacy example notebooks')
def test_nbs():
    pyfolio_root = os.path.dirname(os.path.abspath(pyfolio.__file__))
    path = os.path.join(pyfolio_root, 'examples', '*.ipynb')
    for ipynb in glob.glob(path):
        nb = nbformat.read(ipynb, as_version=4)
        NotebookClient(nb, timeout=600).execute()
