"""CL001 - a value is read by code but defined by no configuration source."""

from __future__ import annotations

from conflint.config import Settings
from conflint.models import Config, Finding, Severity
from conflint.rules.base import Rule

__all__ = ["MissingRule"]


class MissingRule(Rule):
    id = "CL001"
    name = "missing"
    severity = Severity.ERROR
    description = "A configuration value is read by code but defined nowhere."
    fixable = False

    def check(self, config: Config, settings: Settings) -> list[Finding]:
        defined = {entry.name for entry in config.entries}
        findings: list[Finding] = []
        for name, usages in config.usages_by_name().items():
            if settings.is_name_ignored(name) or name in defined:
                continue
            required = any(usage.required for usage in usages)
            severity = Severity.ERROR if required else Severity.WARNING
            where = sorted({str(u.location.relative_to(config.root)) for u in usages})
            findings.append(
                self.finding(
                    f"'{name}' is read in code but not defined in any configuration source",
                    key=name,
                    location=usages[0].location,
                    severity=severity,
                    help="Add it to your .env (then run `confl sync` to refresh .env.example)",
                    data={"usages": where, "required": required},
                )
            )
        return findings
