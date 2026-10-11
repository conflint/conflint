"""Reporter output tests."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

from conflint.config import load_settings
from conflint.engine import Analyzer
from conflint.exceptions import ConfigError
from conflint.reporters import create_reporter


def _report_and_settings(tmp_path, write_files):
    write_files(
        tmp_path,
        {
            "app.py": "import os\nx = os.environ['MISSING_REQUIRED']\n",
            ".env": "UNUSED=1\n",
        },
    )
    settings = load_settings(tmp_path)
    report = Analyzer(settings).run()
    return report, settings


def _render(tmp_path, report, settings, name):
    return create_reporter(name).render(report, settings)


class TestTextReporter:
    def test_summary_embedded(self, tmp_path, write_files):
        report, settings = _report_and_settings(tmp_path, write_files)
        out = _render(tmp_path, report, settings, "text")
        assert "files checked" in out
        assert "CL001" in out
        assert "CL002" in out


class TestJsonReporter:
    def test_structure(self, tmp_path, write_files):
        report, settings = _report_and_settings(tmp_path, write_files)
        payload = json.loads(_render(tmp_path, report, settings, "json"))
        assert payload["schema_version"] == "1.0"
        assert payload["summary"]["counts"]["error"] == 1
        assert payload["findings"][0]["rule"] == "CL001"
        assert {"files_scanned", "usages", "entries"} <= set(payload["summary"])


class TestSarifReporter:
    def test_valid_sarif(self, tmp_path, write_files):
        report, settings = _report_and_settings(tmp_path, write_files)
        payload = json.loads(_render(tmp_path, report, settings, "sarif"))
        runs = payload["runs"]
        assert len(runs) == 1
        driver = runs[0]["tool"]["driver"]
        assert driver["name"] == "conflint"
        rules = {r["id"] for r in driver["rules"]}
        assert {"CL001", "CL002"} <= rules
        results = runs[0]["results"]
        assert any(r["ruleId"] == "CL001" for r in results)


class TestGitHubReporter:
    def test_workflow_commands(self, tmp_path, write_files):
        report, settings = _report_and_settings(tmp_path, write_files)
        out = _render(tmp_path, report, settings, "github")
        assert "::error" in out
        assert "CL001" in out
        assert "::warning" in out


class TestJunitReporter:
    def test_parseable_xml(self, tmp_path, write_files):
        report, settings = _report_and_settings(tmp_path, write_files)
        out = _render(tmp_path, report, settings, "junit")
        root = ET.fromstring(out)
        assert root.tag == "testsuites"
        suites = root.findall("testsuite")
        assert len(suites) == 1
        assert root.find(".//testcase") is not None


class TestReporterSelection:
    def test_all_builtin_names(self, tmp_path, write_files):
        report, settings = _report_and_settings(tmp_path, write_files)
        for name in ("text", "json", "sarif", "github", "junit"):
            assert create_reporter(name).render(report, settings) != ""

    def test_unknown_raises(self):
        with pytest.raises(ConfigError):
            create_reporter("bogus")
