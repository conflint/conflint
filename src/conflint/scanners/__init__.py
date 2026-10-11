"""Built-in scanners.

Imported eagerly by the registry so that ``from conflint.scanners import ...``
is a stable, documented surface.
"""

from __future__ import annotations

from conflint.scanners.base import Scanner
from conflint.scanners.go import GoScanner
from conflint.scanners.javascript import JavaScriptScanner
from conflint.scanners.python import PythonScanner
from conflint.scanners.ruby import RubyScanner

__all__ = [
    "GoScanner",
    "JavaScriptScanner",
    "PythonScanner",
    "RubyScanner",
    "Scanner",
]
