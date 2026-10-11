"""CL008 - a secret-looking value is weak or an obvious default."""

from __future__ import annotations

from conflint.config import Settings
from conflint.models import Config, Finding, Severity
from conflint.rules.base import Rule
from conflint.utils import is_sensitive_name

__all__ = ["WeakSecretRule"]

_WEAK_VALUES = {
    "password",
    "passwd",
    "secret",
    "changeme",
    "change_me",
    "admin",
    "root",
    "123456",
    "12345678",
    "1234567890",
    "qwerty",
    "letmein",
    "default",
    "key",
    "token",
    "test",
    "dev",
    "development",
    "prod",
    "production",
    "true",
    "false",
    "null",
    "none",
}


class WeakSecretRule(Rule):
    id = "CL008"
    name = "weak-secret"
    severity = Severity.WARNING
    description = "A secret-looking value equals a weak or default placeholder."
    fixable = False

    def check(self, config: Config, settings: Settings) -> list[Finding]:
        findings: list[Finding] = []
        for entry in config.entries:
            if entry.is_example or not is_sensitive_name(entry.name):
                continue
            value = entry.value
            if not self._is_weak(entry.name, value):
                continue
            findings.append(
                self.finding(
                    f"'{entry.name}' uses a weak or default value",
                    key=entry.name,
                    location=entry.location,
                    data={"source": entry.source},
                )
            )
        return findings

    @staticmethod
    def _is_weak(name: str, value: str | None) -> bool:
        if value is None:
            return False
        v = value.strip().strip("\"'").lower()
        if not v:
            return False
        if v in _WEAK_VALUES:
            return True
        lowered_name = name.lower()
        return v in {lowered_name, f"your-{lowered_name}", f"your_{lowered_name}"}
