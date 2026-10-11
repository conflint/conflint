"""CL009 - a value is used or provided but missing from the example template."""

from __future__ import annotations

from conflint.config import Settings
from conflint.models import Config, Finding, Location, Severity
from conflint.rules.base import Rule

__all__ = ["UndocumentedRule"]


class UndocumentedRule(Rule):
    id = "CL009"
    name = "undocumented"
    severity = Severity.INFO
    description = "A value is used or provided but not documented in any example file."
    fixable = False

    def check(self, config: Config, settings: Settings) -> list[Finding]:
        if not settings.require_example:
            return []
        example_names = {e.name for e in config.entries if e.is_example}
        if not example_names:
            # No example template exists at all; nothing to be "missing from".
            return []

        findings: list[Finding] = []
        # Names that exist for real (used by code or provided by a real source).
        candidates = set(config.used_names()) | config.real_defined_names()
        location_by_name: dict[str, Location] = {}
        for entry in config.entries:
            location_by_name.setdefault(entry.name, entry.location)
        for usage in config.usages:
            location_by_name.setdefault(usage.name, usage.location)

        for name in sorted(candidates):
            if settings.is_name_ignored(name) or name in example_names:
                continue
            findings.append(
                self.finding(
                    f"'{name}' is not documented in any example file",
                    key=name,
                    location=location_by_name.get(name),
                    help="Run `confl sync` to regenerate your .env.example",
                    data={"example_files": list(settings.example_files)},
                )
            )
        return findings
