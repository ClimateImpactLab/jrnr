# -*- coding: utf-8 -*-

"""Top-level package for jrnr."""

from __future__ import absolute_import
from jrnr.jrnr import slurm_runner

__author__ = """Justin Simcock"""
__email__ = 'jsimcock@rhg.com'
__version__ = '0.2.1'

_module_imports = (
    slurm_runner,
)

__all__ = list(map(lambda x: x.__name__, _module_imports))
