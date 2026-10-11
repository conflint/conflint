"""Shared YAML loading for the YAML-based sources."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import yaml

__all__ = ["load_all", "load_documents"]


def load_all(text: str) -> list[Any]:
    """Parse every YAML document in ``text``; return ``[]`` on any error."""

    try:
        return list(yaml.safe_load_all(text))
    except yaml.YAMLError:
        return []


def load_documents(text: str) -> Iterator[Any]:
    for document in load_all(text):
        if document is not None:
            yield document
