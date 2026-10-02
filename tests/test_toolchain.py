"""Trivial test: the toolchain runs the Python the project pins, and the core package imports."""

import sys

import rmi_core


def test_python_is_the_pinned_minor() -> None:
    assert sys.version_info[:2] == (3, 12)


def test_core_package_imports() -> None:
    assert rmi_core.__doc__
