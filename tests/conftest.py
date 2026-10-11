"""Shared fixtures for the test-suite."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import pytest

if sys.version_info >= (3, 11):
    pass  # type: ignore[no-redef]
else:  # pragma: no cover - exercised on 3.9/3.10
    pass  # type: ignore[no-redef]


@pytest.fixture
def write_files() -> Callable[[Path, dict[str, str]], Path]:
    """Create nested files under a root directory; return the root."""

    def _write(root: Path, files: dict[str, str]) -> Path:
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    return _write


@pytest.fixture
def run_rules():
    """Run a rule against an ad-hoc usage/entry model."""

    from conflint.config import Settings
    from conflint.models import Config

    def _run(rule, usages=(), entries=(), root=None, settings=None):
        model = Config(root=root or Path.cwd(), usages=list(usages), entries=list(entries))
        return rule.check(model, settings or Settings(root=model.root))

    return _run
