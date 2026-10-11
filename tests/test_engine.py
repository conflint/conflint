"""Integration tests: end-to-end analysis of a small project tree."""

from __future__ import annotations

from conflint.config import load_settings
from conflint.engine import Analyzer


def _analyze(root):
    return Analyzer(load_settings(root)).run()


def _rules(report):
    return {f.rule_id for f in report.findings}


def _by_rule(report):
    counts = {}
    for f in report.findings:
        counts[f.rule_id] = counts.get(f.rule_id, 0) + 1
    return counts


class TestBasicProject:
    def test_pipeline_counts(self, tmp_path, write_files):
        write_files(
            tmp_path,
            {
                "app.py": "import os\nx = os.environ['REQUIRED_MISSING']\n"
                "y = os.getenv('PRESENT')\n",
                ".env": "PRESENT=1\nUNUSED=2\n",
                ".env.example": "PRESENT=1\n",
            },
        )
        report = _analyze(tmp_path)
        assert report.files_scanned == 3
        assert report.usages == 2
        assert report.entries == 3

        counts = _by_rule(report)
        # REQUIRED_MISSING: missing everywhere + undocumented.
        assert counts["CL001"] == 1
        # UNUSED is real-defined and neither read nor documented.
        assert counts["CL009"] == 2
        assert counts["CL002"] == 1

    def test_gitignored_env_still_scanned(self, tmp_path, write_files):
        write_files(
            tmp_path,
            {
                ".gitignore": ".env\n",
                "app.py": "import os\nx = os.getenv('SECRET_A')\n",
                ".env": "SECRET_A=a\n",
            },
        )
        report = _analyze(tmp_path)
        assert report.entries == 1
        # No CL001 because .env (though gitignored) was parsed.
        assert "CL001" not in _rules(report)

    def test_code_files_respect_gitignore(self, tmp_path, write_files):
        write_files(
            tmp_path,
            {
                ".gitignore": "vendor/\n",
                "app.py": "import os\nx = os.getenv('K')\n",
                "vendor/bundle.py": "import os\ny = os.environ['VENDOR_SECRET']\n",
                ".env": "K=1\n",
            },
        )
        report = _analyze(tmp_path)
        assert report.files_scanned == 2
        keys = {f.key for f in report.findings}
        assert "VENDOR_SECRET" not in keys


class TestSeverityOverrides:
    def test_disable_rule(self, tmp_path, write_files):
        write_files(
            tmp_path,
            {
                "conflint.toml": 'disable = ["CL001"]\n',
                "app.py": "import os\nx = os.environ['MISSING']\n",
            },
        )
        report = _analyze(tmp_path)
        assert "CL001" not in _rules(report)
        assert report.findings == []

    def test_severity_override(self, tmp_path, write_files):
        write_files(
            tmp_path,
            {
                "conflint.toml": 'enable = { CL009 = "error" }\n',
                "app.py": "import os\nx = os.getenv('MISSING_DOC')\n",
                ".env.example": "OTHER=1\n",
            },
        )
        report = _analyze(tmp_path)
        cl009 = [f for f in report.findings if f.rule_id == "CL009"]
        assert cl009 and cl009[0].severity.value == "error"


class TestSelection:
    def test_only_python_scanner(self, tmp_path, write_files):
        write_files(
            tmp_path,
            {
                "app.py": "import os\nx = os.getenv('PY_VAR')\n",
                "config.ts": "const x = process.env.TS_VAR;\n",
                ".env": "PY_VAR=1\n",
                "conflint.toml": 'scanners = ["python"]\n',
            },
        )
        report = _analyze(tmp_path)
        keys = {f.key for f in report.findings}
        assert "TS_VAR" not in keys
