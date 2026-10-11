"""JUnit XML output for tools that expect test-style reports (Jenkins,
GitLab dashboards, ``pytest`` dashboards, ...).

Each finding becomes a ``testcase``; findings become ``failure`` children when
the run fails, ``skipped`` otherwise (mirroring how linters are consumed).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from conflint.config import Settings
from conflint.models import Finding, Report
from conflint.reporters.base import Reporter

__all__ = ["JunitReporter"]


class JunitReporter(Reporter):
    name = "junit"
    description = "JUnit XML report (CI dashboards)."

    def render(self, report: Report, settings: Settings) -> str:
        findings = report.sorted_findings()
        failed = sum(1 for f in findings if f.severity.rank >= settings.fail_level.rank)

        suites = ET.Element("testsuites", {"name": "conflint"})
        testsuite = ET.SubElement(
            suites,
            "testsuite",
            {
                "name": "conflint",
                "tests": str(len(findings)),
                "failures": str(failed),
                "errors": "0",
                "skipped": str(len(findings) - failed),
            },
        )
        for finding in findings:
            case = ET.SubElement(
                testsuite,
                "testcase",
                {
                    "classname": finding.rule_id,
                    "name": finding.key or finding.message[:60],
                    "file": self._uri(finding, settings),
                },
            )
            tag = "failure" if finding.severity.rank >= settings.fail_level.rank else "skipped"
            node = ET.SubElement(case, tag, {"message": f"{finding.message} ({finding.rule_id})"})
            node.text = finding.help or finding.message

        tree = ET.ElementTree(suites)
        return _serialize(tree)

    @staticmethod
    def _uri(finding: Finding, settings: Settings) -> str:
        if finding.location is None:
            return ""
        loc = finding.location
        return str(loc.relative_to(settings.root) if settings.root else loc.path)


def _serialize(tree: ET.ElementTree) -> str:
    import io

    buffer = io.StringIO()
    ET.indent(tree, space="  ")  # Python 3.9+
    tree.write(buffer, encoding="unicode", xml_declaration=False)
    return buffer.getvalue() + "\n"
