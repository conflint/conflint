"""CL005 - documented but not actually provided (example/real drift)."""

from __future__ import annotations

from typing import List

from conflint.config import Settings
from conflint.models import Config, Finding, Severity
from conflint.rules.base import Rule

__all__ = ["DriftRule"]


class DriftRule(Rule):
    id = "CL005"
    name = "drift"
    severity = Severity.ERROR
    description = "A value is documented in an example file but provided by no real source."
    fixable = False

    def check(self, config: Config, settings: Settings) -> List[Finding]:
        example_names = {e.name for e in config.entries if e.is_example}
        real_names = {e.name for e in config.entries if not e.is_example}
        findings: List[Finding] = []
        for name, usages in config.usages_by_name().items():
            if settings.is_name_ignored(name):
                continue
            if name in example_names and name not in real_names:
                findings.append(
                    self.finding(
                        f"'{name}' is used by code and documented in an example, "
                        f"but no real source provides it",
                        key=name,
                        location=usages[0].location,
                        severity=Severity.ERROR,
                        help="Add it to your .env / compose / k8s so it exists at runtime",
                        data={"documented": True, "provided": False},
                    )
                )
        return findings
