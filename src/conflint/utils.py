"""Small, dependency-free helpers used across conflint."""

from __future__ import annotations

import math
import os
import re
from collections.abc import Hashable, Iterable, Sequence
from pathlib import Path
from typing import TypeVar

_T = TypeVar("_T")

__all__ = [
    "chunk",
    "close_matches",
    "dedupe_preserve_order",
    "guess_prefix",
    "humanize_ms",
    "is_sensitive_name",
    "is_valid_env_name",
    "levenshtein",
    "looks_like_secret",
    "read_text",
    "relative_display",
    "shannon_entropy",
    "strip_quotes",
    "tokenize_env_name",
]

_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Substrings that strongly imply a value is a secret.  Kept deliberately broad;
# rules combine this with entropy/format heuristics before flagging anything.
_SENSITIVE_MARKERS = (
    "secret",
    "token",
    "password",
    "passwd",
    "pwd",
    "apikey",
    "api_key",
    "access_key",
    "secret_key",
    "private_key",
    "credential",
    "auth",
    "bearer",
    "session_key",
    "signing_key",
    "encryption_key",
    "client_secret",
    "refresh_token",
    "webhook_url",
    "database_url",
    "dsn",
)


def read_text(path: Path, *, encoding: str = "utf-8") -> str:
    """Read a file as text, tolerating BOMs and invalid bytes.

    confint scans user repositories, so it must never crash on a stray
    non-UTF-8 byte.  Undecodable input is replaced rather than raising.
    """

    try:
        data = path.read_bytes()
    except OSError as exc:  # pragma: no cover - depends on filesystem
        raise OSError(f"cannot read {path}: {exc}") from exc

    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.decode(encoding, errors="replace")


def strip_quotes(value: str | None) -> str | None:
    """Remove a single matching pair of surrounding quotes and trim spaces."""

    if value is None:
        return None
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def levenshtein(a: str, b: str) -> int:
    """Iterative Levenshtein edit distance (case-sensitive)."""

    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (ca != cb)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def close_matches(
    needle: str,
    haystack: Iterable[str],
    *,
    max_distance: int = 2,
    limit: int = 3,
) -> list[tuple[str, int]]:
    """Return ``(candidate, distance)`` pairs close to ``needle``.

    Case-insensitive distance is used so that ``dbhost`` matches ``DB_HOST``
    with a distance of one (the separator) rather than several.
    """

    lowered = needle.lower().replace("-", "_")
    scored: list[tuple[str, int]] = []
    for candidate in haystack:
        if candidate == needle:
            continue
        dist = levenshtein(lowered, candidate.lower().replace("-", "_"))
        if dist <= max_distance:
            scored.append((candidate, dist))
    scored.sort(key=lambda item: (item[1], item[0]))
    return scored[:limit]


def tokenize_env_name(name: str) -> list[str]:
    """Split an env-style name into lower-cased word tokens."""

    return [t for t in re.split(r"[^A-Za-z0-9]+", name.lower()) if t]


def guess_prefix(name: str) -> str:
    """Best-effort component prefix, e.g. ``DB_HOST`` -> ``DB``."""

    tokens = tokenize_env_name(name)
    return tokens[0] if tokens else ""


def is_sensitive_name(name: str) -> bool:
    """Heuristic: does the *name* suggest the value is a secret?"""

    lowered = name.lower()
    return any(marker in lowered for marker in _SENSITIVE_MARKERS)


#: Values that are obviously not real secrets and should never be flagged.
_PLACEHOLDER_VALUES = {
    "",
    "changeme",
    "change_me",
    "change-me",
    "todo",
    "your-key-here",
    "your_key_here",
    "placeholder",
    "example",
    "xxx",
    "test",
    "password",
    "secret",
    "admin",
    "root",
    "123456",
    "12345678",
    "none",
    "null",
    "false",
    "true",
}


def shannon_entropy(value: str) -> float:
    """Shannon entropy (bits per character) of ``value``."""

    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for char in value:
        counts[char] = counts.get(char, 0) + 1
    length = len(value)
    total = 0.0
    for count in counts.values():
        total += (count / length) * math.log2(count / length)
    return -total


def looks_like_secret(value: str | None, *, entropy_threshold: float = 3.5) -> bool:
    """Heuristic: does ``value`` look like a real, high-entropy secret?

    Real secrets are long, mix character classes, avoid whitespace and exceed a
    Shannon-entropy threshold.  Obvious placeholders are rejected outright.
    """

    if not value:
        return False
    v = value.strip()
    if v.lower() in _PLACEHOLDER_VALUES:
        return False
    if len(v) < 12:
        return False
    if any(ch.isspace() for ch in v):
        return False
    has_alpha = any(ch.isalpha() for ch in v)
    has_digit = any(ch.isdigit() for ch in v)
    has_symbol = any(not ch.isalnum() for ch in v)
    if not (has_alpha and (has_digit or has_symbol)):
        return False
    return shannon_entropy(v) >= entropy_threshold


def chunk(items: Sequence[_T], size: int) -> Iterable[Sequence[_T]]:
    """Yield consecutive slices of ``items`` of length ``size``."""

    if size <= 0:
        raise ValueError("size must be positive")
    for start in range(0, len(items), size):
        yield items[start : start + size]


def dedupe_preserve_order(items: Iterable[Hashable]) -> list[Hashable]:
    """Return unique items keeping first-seen order (items must be hashable)."""

    seen: set[Hashable] = set()
    out: list[Hashable] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def humanize_ms(value: float) -> str:
    """Render a millisecond duration compactly."""

    if value < 1000:
        return f"{value:.0f}ms"
    return f"{value / 1000:.2f}s"


def relative_display(path: Path, root: Path | None) -> str:
    """Render ``path`` relative to ``root`` when possible."""

    if root is None:
        return str(path)
    try:
        return os.path.relpath(path, root)
    except (ValueError, OSError):  # pragma: no cover - cross-drive on Windows
        return str(path)


def is_valid_env_name(name: str) -> bool:
    """Whether ``name`` is a legal POSIX environment variable identifier."""

    return bool(_ENV_NAME_RE.match(name))
