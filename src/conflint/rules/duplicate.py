"""CL007 - the same name is defined more than once in a file, or conflicts."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from conflint.config import Settings
from conflint.models import Config, Entry, Finding, Severity
from conflint.rules.base import Rule

__all__ = ["DuplicateRule"]


class DuplicateRule(Rule):
    id = "CL007"
    name = "duplicate"
    severity = Severity.WARNING
    description = "A key is defined more than once, or real sources disagree on its value."
    fixable = False

    def check(self, config: Config, settings: Settings) -> List[Finding]:
        findings: List[Finding] = []
        findings.extend(self._duplicates_in_file(config, settings))
        findings.extend(self._conflicting_values(config, settings))
        return findings

    def _duplicates_in_file(self, config: Config, settings: Settings) -> List[Finding]:
        by_file: Dict[Tuple[Path, str], List[Entry]] = defaultdict(list)
        for entry in config.entries:
            by_file[(entry.location.path, entry.name)].append(entry)

        findings: List[Finding] = []
        for (path, name), entries in by_file.items():
            if len(entries) < 2 or settings.is_name_ignored(name):
                continue
            findings.append(
                self.finding(
                    f"'{name}' is defined {len(entries)} times in {path.name}",
                    key=name,
                    location=entries[-1].location,
                    help="Keep a single definition; later values silently win",
                    data={"count": len(entries)},
                )
            )
        return findings

    def _conflicting_values(self, config: Config, settings: Settings) -> List[Finding]:
        by_name: Dict[str, List[Entry]] = defaultdict(list)
        for entry in config.entries:
            if not entry.is_example and not entry.is_empty:
                by_name[entry.name].append(entry)

        findings: List[Finding] = []
        for name, entries in by_name.items():
            if settings.is_name_ignored(name):
                continue
            values = {e.value for e in entries}
            if len(values) > 1 and len({e.source for e in entries}) > 1:
                sources = sorted({e.source for e in entries})
                findings.append(
                    self.finding(
                        f"'{name}' has conflicting values across sources: {', '.join(sources)}",
                        key=name,
                        location=entries[0].location,
                        severity=Severity.INFO,
                        data={"sources": sources},
                    )
                )
        return findings
