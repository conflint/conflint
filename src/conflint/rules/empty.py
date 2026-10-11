"""CL006 - a required value is defined with an empty value."""

from __future__ import annotations

from typing import List

from conflint.config import Settings
from conflint.models import Config, Finding, Severity
from conflint.rules.base import Rule

__all__ = ["EmptyValueRule"]


class EmptyValueRule(Rule):
    id = "CL006"
    name = "empty-value"
    severity = Severity.WARNING
    description = "A value required by code is defined but left empty."
    fixable = False

    def check(self, config: Config, settings: Settings) -> List[Finding]:
        required_names = {
            usage.name for usage in config.usages if usage.required
        }
        findings: List[Finding] = []
        seen = set()
        for entry in config.entries:
            if entry.is_example or entry.name in seen:
                continue
            if entry.name in required_names and entry.is_empty:
                if settings.is_name_ignored(entry.name):
                    continue
                seen.add(entry.name)
                findings.append(
                    self.finding(
                        f"'{entry.name}' is required by code but defined empty in {entry.source}",
                        key=entry.name,
                        location=entry.location,
                        data={"source": entry.source},
                    )
                )
        return findings
