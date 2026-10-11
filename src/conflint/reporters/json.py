"""Structured JSON output (stable schema for tooling)."""

from __future__ import annotations

import json
from typing import Any, Dict

from conflint.config import Settings
from conflint.models import Report
from conflint.reporters.base import Reporter
from conflint.version import __version__

__all__ = ["JsonReporter"]

_SCHEMA_VERSION = "1.0"


class JsonReporter(Reporter):
    name = "json"
    description = "Machine-readable JSON report."

    def render(self, report: Report, settings: Settings) -> str:
        payload: Dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "conflint_version": __version__,
            "root": str(settings.root),
            "summary": {
                "files_scanned": report.files_scanned,
                "usages": report.usages,
                "entries": report.entries,
                "duration_ms": round(report.duration_ms, 3),
                "counts": report.count_by_severity(),
            },
            "sources": [summary.as_dict() for summary in report.sources],
            "findings": [
                finding.as_dict(settings.root) for finding in report.sorted_findings()
            ],
        }
        return json.dumps(payload, indent=2, sort_keys=False) + "\n"