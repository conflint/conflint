"""CL004 - a real secret appears to be committed in a configuration source."""

from __future__ import annotations

from conflint.config import Settings
from conflint.models import Config, Finding, Severity
from conflint.rules.base import Rule
from conflint.utils import is_sensitive_name, looks_like_secret

__all__ = ["SecretLeakRule"]


class SecretLeakRule(Rule):
    id = "CL004"
    name = "secret-leak"
    severity = Severity.ERROR
    description = "A high-entropy secret value is committed in a real config source."
    fixable = False

    def check(self, config: Config, settings: Settings) -> list[Finding]:
        findings: list[Finding] = []
        for entry in config.entries:
            if entry.is_example or entry.is_empty:
                continue
            if not (entry.is_secret or is_sensitive_name(entry.name)):
                continue
            if not looks_like_secret(entry.value, entropy_threshold=settings.entropy_threshold):
                continue
            findings.append(
                self.finding(
                    f"'{entry.name}' looks like a committed secret in {entry.source}",
                    key=entry.name,
                    location=entry.location,
                    severity=Severity.ERROR,
                    help="Move real secrets to a secrets manager; keep placeholders in .env.example",
                    data={"source": entry.source},
                )
            )
        return findings
