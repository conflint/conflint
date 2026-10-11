"""Human-friendly terminal output built on Rich.

Findings are grouped by file, then by severity.  A summary line mirrors the
exit code so ``confl check`` stays legible on a single screen.
"""

from __future__ import annotations

import io
from collections import OrderedDict
from pathlib import Path
from typing import Any, cast

from rich.console import Console
from rich.table import Table

from conflint.config import Settings
from conflint.models import Finding, Report, Severity
from conflint.reporters.base import Reporter
from conflint.utils import humanize_ms

__all__ = ["TextReporter"]

_SEVERITY_STYLE = {
    Severity.ERROR: "red bold",
    Severity.WARNING: "yellow bold",
    Severity.INFO: "cyan bold",
}


class TextReporter(Reporter):
    name = "text"
    description = "Colored, grouped-by-file output for humans."

    def render(self, report: Report, settings: Settings) -> str:
        console = Console(
            file=io.StringIO(),
            color_system=cast(Any, _color_system(settings.color)),
            width=120,
            highlight=False,
        )

        header = Table.grid(padding=(0, 1))
        header.add_column(style="bold", justify="right")
        header.add_column()
        header.add_row(
            "conflint",
            f"checked {report.files_scanned} files "
            f"({report.usages} config reads, {report.entries} definitions) in {humanize_ms(report.duration_ms)}",
        )
        console.print(header)
        console.print("")

        groups = self._group_by_file(report.sorted_findings(), settings.root)
        if not groups:
            console.print("[green bold]No configuration issues found.[/green bold]")
        else:
            self._print_groups(console, groups)

        counts = report.count_by_severity()
        summary = (
            f"[bold]{report.files_scanned} files checked[/bold] - "
            f"[red]{counts[Severity.ERROR.value]}[/red] errors, "
            f"[yellow]{counts[Severity.WARNING.value]}[/yellow] warnings, "
            f"[cyan]{counts[Severity.INFO.value]}[/cyan] infos"
        )
        console.print("")
        console.print(summary)
        return cast(io.StringIO, console.file).getvalue()

    @staticmethod
    def _group_by_file(
        findings: list[Finding], root: Path | None
    ) -> OrderedDict[str, list[Finding]]:
        groups: OrderedDict[str, list[Finding]] = OrderedDict()
        for finding in findings:
            if finding.location is not None:
                path = str(finding.location.relative_to(root) if root else finding.location.path)
            else:
                path = "(project)"
            groups.setdefault(path, []).append(finding)
        return groups

    def _print_groups(self, console: Console, groups: dict[str, list[Finding]]) -> None:
        for path, findings in groups.items():
            console.print(f"[bold underline]{path}[/bold underline]")
            for finding in findings:
                style = _SEVERITY_STYLE[finding.severity]
                rule = f"[{style}]{finding.rule_id}[/{style}]"
                loc = ""
                if finding.location and finding.location.line:
                    loc = f":[bold]{finding.location.line}[/bold]"
                console.print(f"  {rule} {finding.severity.value}: {finding.message}{loc}")
                if finding.help:
                    console.print(f"    [dim]hint: {finding.help}[/dim]")
            console.print("")


def _color_system(configured: bool | None) -> str | None:
    if configured is False:
        return None
    return "auto"
