"""SARIF 2.1.0 output, the report format understood by GitHub CodeQL,
GitLab, Azure Pipelines and most CI security dashboards.

A rule table is emitted once with stable metadata so consumers can render
consistent findings across runs.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from conflint.config import Settings
from conflint.models import Finding, Report, Severity
from conflint.reporters.base import Reporter
from conflint.version import __version__

__all__ = ["SarifReporter"]

_LEVEL = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
}

_URI = "https://github.com/confl/conflint"


class SarifReporter(Reporter):
    name = "sarif"
    description = "SARIF 2.1.0 for CI security dashboards."

    def render(self, report: Report, settings: Settings) -> str:
        run: Dict[str, Any] = {
            "tool": {
                "driver": {
                    "name": "conflint",
                    "version": __version__,
                    "informationUri": _URI,
                    "rules": self._rule_metadata(),
                }
            },
            "results": [self._result(f, settings) for f in report.sorted_findings()],
        }
        payload = {
            "$schema": (
                "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/"
                "master/Schemata/sarif-schema-2.1.0.json"
            ),
            "version": "2.1.0",
            "runs": [run],
        }
        return json.dumps(payload, indent=2) + "\n"

    @staticmethod
    def _rule_metadata() -> List[Dict[str, Any]]:
        rules: Dict[str, Dict[str, Any]] = {}
        for rule in _collect_rules():
            default = rule.severity.value
            rules[rule.id] = {
                "id": rule.id,
                "name": rule.name,
                "shortDescription": {"text": rule.description},
                "help": {
                    "text": f"{rule.description} See the rule documentation for details."
                },
                "security-severity": "7.0"
                if default == "error"
                else ("5.0" if default == "warning" else "2.0"),
                "defaultConfiguration": {"level": _LEVEL[rule.severity]},
            }
        return list(rules.values())

    def _result(self, finding: Finding, settings: Settings) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "ruleId": finding.rule_id,
            "level": _LEVEL[finding.severity],
            "message": {"text": finding.message},
        }
        if finding.key:
            result["properties"] = {"key": finding.key}
        if finding.location is not None:
            loc = finding.location
            uri = str(loc.relative_to(settings.root) if settings.root else loc.path)
            region: Dict[str, Any] = {}
            if loc.line:
                region["startLine"] = loc.line
            if loc.column:
                region["startColumn"] = loc.column
            result["locations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": uri},
                        "region": region,
                    }
                }
            ]
        return result


def _collect_rules():
    from conflint.registry import get_rules

    return list(get_rules().values())