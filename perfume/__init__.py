# -*- coding: utf-8 -*-

"""Top-level package for perfume."""

from .perfume import bench  # noqa: F401
from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

__author__ = """Leif Walsh"""
__email__ = "leif.walsh@gmail.com"
__all__ = ["bench"]
