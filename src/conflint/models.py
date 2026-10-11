"""Core data model shared by scanners, sources, rules and reporters.

The mental model is small and deliberate:

* A :class:`Usage`      is a place in **source code** that *reads* a value.
* An :class:`Entry`     is a place in a **configuration source** that *defines* a value.
* A :class:`Finding`    is a **rule** verdict that links the two (or complains about one).

Scanners fill ``Usage`` objects, sources fill ``Entry`` objects, and rules turn
the reconciled graph of usages/entries into findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

__all__ = [
    "Severity",
    "Language",
    "Location",
    "Usage",
    "Entry",
    "Finding",
    "Report",
    "Config",
    "SourceSummary",
]


class Severity(str, Enum):
    """Severity of a finding.  Higher-ranked severities decide exit codes."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"error": 3, "warning": 2, "info": 1}[self.value]

    @classmethod
    def coerce(cls, value: "Severity | str") -> "Severity":
        if isinstance(value, Severity):
            return value
        return cls(str(value).lower())

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Severity):
            return NotImplemented
        return self.rank < other.rank


class Language(str, Enum):
    """Source languages understood by the built-in scanners."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUBY = "ruby"
    SHELL = "shell"
    GENERIC = "generic"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True)
class Location:
    """A point in a file.  ``line``/``column`` are 1-based; ``0`` means unknown."""

    path: Path
    line: int = 0
    column: int = 0

    def __str__(self) -> str:
        if self.line:
            return f"{self.path}:{self.line}:{self.column}"
        return str(self.path)

    def relative_to(self, root: Path) -> "Location":
        try:
            rel = self.path.resolve().relative_to(root.resolve())
        except (ValueError, OSError):
            rel = self.path
        return Location(rel, self.line, self.column)

    def as_dict(self) -> Dict[str, Any]:
        return {"path": str(self.path), "line": self.line, "column": self.column}


@dataclass
class Usage:
    """A read of a configuration value from source code."""

    name: str
    location: Location
    language: Language = Language.GENERIC
    read_via: str = ""
    required: bool = False
    has_default: bool = False
    default: Optional[str] = None
    notes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Usage.name must not be empty")

    @property
    def is_optional(self) -> bool:
        return self.has_default

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "location": self.location.as_dict(),
            "language": self.language.value,
            "read_via": self.read_via,
            "required": self.required,
            "has_default": self.has_default,
            "default": self.default,
        }


@dataclass
class Entry:
    """A definition of a configuration value from a known source."""

    name: str
    value: Optional[str]
    location: Location
    source: str
    is_secret: bool = False
    is_example: bool = False
    notes: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Entry.name must not be empty")

    @property
    def is_empty(self) -> bool:
        return self.value is None or self.value.strip() == ""

    @property
    def is_placeholder(self) -> bool:
        if self.value is None:
            return True
        v = self.value.strip().strip("\"'").lower()
        return v in {"", "changeme", "change_me", "todo", "your-key-here", "xxx", "placeholder"}

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "location": self.location.as_dict(),
            "source": self.source,
            "is_secret": self.is_secret,
            "is_example": self.is_example,
        }


@dataclass
class Finding:
    """A single rule verdict."""

    rule_id: str
    severity: Severity
    message: str
    key: Optional[str] = None
    location: Optional[Location] = None
    help: Optional[str] = None
    fixable: bool = False
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def sort_key(self) -> Tuple[int, str, str, int, int]:
        loc = self.location
        path = str(loc.path) if loc else ""
        line = loc.line if loc else 0
        col = loc.column if loc else 0
        return (-self.severity.rank, path, self.rule_id, line, col)

    def as_dict(self, root: Optional[Path] = None) -> Dict[str, Any]:
        loc = self.location
        location = None
        if loc is not None:
            location = (loc.relative_to(root) if root else loc).as_dict()
        return {
            "rule": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "key": self.key,
            "location": location,
            "help": self.help,
            "fixable": self.fixable,
            "data": self.data,
        }


@dataclass
class SourceSummary:
    """Aggregate information about one configuration source."""

    name: str
    files: Tuple[Path, ...] = ()
    entries: int = 0
    is_example: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "files": [str(f) for f in self.files],
            "entries": self.entries,
            "is_example": self.is_example,
        }


@dataclass
class Config:
    """The reconciled view of a project's configuration.

    Built by the engine and consumed by rules.  Everything rules need is
    reachable from here without touching the filesystem again.
    """

    root: Path
    usages: List[Usage] = field(default_factory=list)
    entries: List[Entry] = field(default_factory=list)
    sources: List[SourceSummary] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)

    # -- derived indexes -------------------------------------------------
    def usages_by_name(self) -> Dict[str, List[Usage]]:
        index: Dict[str, List[Usage]] = {}
        for usage in self.usages:
            index.setdefault(usage.name, []).append(usage)
        return index

    def entries_by_name(self) -> Dict[str, List[Entry]]:
        index: Dict[str, List[Entry]] = {}
        for entry in self.entries:
            index.setdefault(entry.name, []).append(entry)
        return index

    def entries_by_source(self, source: str) -> List[Entry]:
        return [e for e in self.entries if e.source == source]

    def defined_names(self, *, include_examples: bool = True) -> Set[str]:
        return {
            e.name
            for e in self.entries
            if include_examples or not e.is_example
        }

    def real_defined_names(self) -> Set[str]:
        """Names defined by a *non-example* source (what will exist at runtime)."""
        return {e.name for e in self.entries if not e.is_example}

    def used_names(self) -> Set[str]:
        return {u.name for u in self.usages}

    def iter_names(self) -> Iterator[str]:
        seen = set()
        for u in self.usages:
            if u.name not in seen:
                seen.add(u.name)
                yield u.name
        for e in self.entries:
            if e.name not in seen:
                seen.add(e.name)
                yield e.name


@dataclass
class Report:
    """The complete result of a run."""

    findings: List[Finding] = field(default_factory=list)
    usages: int = 0
    entries: int = 0
    files_scanned: int = 0
    duration_ms: float = 0.0
    sources: List[SourceSummary] = field(default_factory=list)

    def sorted_findings(self) -> List[Finding]:
        return sorted(self.findings, key=lambda f: f.sort_key)

    def count_by_severity(self) -> Dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts

    @property
    def max_severity(self) -> Optional[Severity]:
        if not self.findings:
            return None
        return max(f.severity for f in self.findings)

    def has_findings_at_or_above(self, severity: Severity) -> bool:
        return any(f.severity.rank >= severity.rank for f in self.findings)
