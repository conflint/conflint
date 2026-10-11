"""GitHub Actions workflow-command output.

Emits ``::error`` / ``::warning`` / ``::notice`` lines that GitHub renders as
inline annotations on pull requests, grouped into the check run summary.
"""

from __future__ import annotations

from conflint.config import Settings
from conflint.models import Finding, Report, Severity
from conflint.reporters.base import Reporter

__all__ = ["GithubReporter"]

_COMMAND = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "notice",
}


class GithubReporter(Reporter):
    name = "github"
    description = "GitHub Actions workflow commands (inline PR annotations)."

    def render(self, report: Report, settings: Settings) -> str:
        lines = []
        for finding in report.sorted_findings():
            lines.append(_command(finding, settings))
        return "\n".join(lines) + ("\n" if lines else "")


def _command(finding: Finding, settings: Settings) -> str:
    parts = [f"title={finding.rule_id}"]
    if finding.location is not None:
        loc = finding.location
        uri = str(loc.relative_to(settings.root) if settings.root else loc.path)
        parts.append(f"file={uri}")
        if loc.line:
            parts.append(f"line={loc.line}")
        if loc.column:
            parts.append(f"col={loc.column}")
    props = ",".join(parts)
    message = finding.message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return f"::{_COMMAND[finding.severity]} {props}::{message}"
