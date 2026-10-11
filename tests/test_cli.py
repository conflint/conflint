"""CLI tests via Click's CliRunner."""

from __future__ import annotations

from click.testing import CliRunner

from conflint.cli import main


def _run(args, monkeypatch, cwd):
    monkeypatch.chdir(cwd)
    return CliRunner().invoke(main, args, catch_exceptions=False)


class TestCheck:
    def test_exit_codes_and_summary(self, tmp_path, write_files, monkeypatch):
        write_files(
            tmp_path,
            {
                "app.py": "import os\nx = os.environ['MISSING']\n",
                ".env": "UNUSED=1\n",
            },
        )
        result = _run(["check", str(tmp_path)], monkeypatch, ".")
        assert result.exit_code == 1
        assert "files checked" in result.output
        assert "CL001" in result.output

    def test_clean_exit_zero(self, tmp_path, write_files, monkeypatch):
        write_files(
            tmp_path,
            {
                "app.py": "import os\nx = os.getenv('OK')\n",
                ".env": "OK=1\n",
                ".env.example": "OK=1\n",
            },
        )
        result = _run(["check", str(tmp_path)], monkeypatch, ".")
        assert result.exit_code == 0
        assert "No configuration issues found" in result.output

    def test_json_flag(self, tmp_path, write_files, monkeypatch):
        write_files(
            tmp_path,
            {
                "app.py": "import os\nx = os.environ['MISSING']\n",
                ".env": "X=1\n",
            },
        )
        result = _run(["check", "--json", str(tmp_path)], monkeypatch, ".")
        assert result.exit_code == 1
        assert result.output.strip().startswith("{")

    def test_fail_level_overrides_exit(self, tmp_path, write_files, monkeypatch):
        write_files(
            tmp_path,
            {
                "app.py": "import os\nx = os.getenv('MISSING_OPTIONAL')\n",
                ".env": "UNUSED=1\n",
            },
        )
        result = _run(["check", "--fail-level", "error", str(tmp_path)], monkeypatch, ".")
        # Only warning/info-level findings exist -> no failures, exit 0.
        assert result.exit_code == 0

    def test_empty_project_passes(self, tmp_path, monkeypatch):
        result = _run(["check", str(tmp_path)], monkeypatch, ".")
        assert result.exit_code == 0


class TestOtherCommands:
    def test_rules(self, monkeypatch):
        result = _run(["rules"], monkeypatch, ".")
        assert result.exit_code == 0
        assert "CL001" in result.output
        assert "CL009" in result.output

    def test_init_creates_template(self, tmp_path, monkeypatch):
        result = _run(["init"], monkeypatch, tmp_path)
        assert result.exit_code == 0
        assert (tmp_path / "conflint.toml").exists()

    def test_init_refuses_overwrite(self, tmp_path, write_files, monkeypatch):
        write_files(tmp_path, {"conflint.toml": "x"})
        result = _run(["init"], monkeypatch, tmp_path)
        assert result.exit_code == 2

    def test_sync_creates_example(self, tmp_path, write_files, monkeypatch):
        write_files(tmp_path, {"app.py": "import os\nx=os.getenv('A')\n"})
        result = _run(["sync"], monkeypatch, tmp_path)
        assert result.exit_code == 0
        assert (tmp_path / ".env.example").exists()

    def test_sync_dry_run_no_write(self, tmp_path, write_files, monkeypatch):
        write_files(tmp_path, {"app.py": "import os\nx=os.getenv('A')\n"})
        result = _run(["sync", "--dry-run"], monkeypatch, tmp_path)
        assert result.exit_code == 0
        assert "A=" in result.output
        assert not (tmp_path / ".env.example").exists()

    def test_explain_known_key(self, tmp_path, write_files, monkeypatch):
        write_files(
            tmp_path,
            {
                "app.py": "import os\nx = os.getenv('HOST')\n",
                ".env": "HOST=localhost\n",
            },
        )
        result = _run(["explain", "HOST"], monkeypatch, tmp_path)
        assert result.exit_code == 0
        assert "localhost" in result.output
        assert "place(s)" in result.output

    def test_explain_unknown_key(self, tmp_path, monkeypatch):
        result = _run(["explain", "NOPE"], monkeypatch, tmp_path)
        assert result.exit_code == 1
        assert "not used or defined" in result.output

    def test_version(self, monkeypatch):
        result = _run(["version"], monkeypatch, ".")
        assert result.exit_code == 0
        assert result.output.startswith("confl")


class TestConfigErrors:
    def test_invalid_config_is_fatal(self, tmp_path, write_files, monkeypatch):
        write_files(tmp_path, {"conflint.toml": "bogus = true\n"})
        result = _run(["check", str(tmp_path)], monkeypatch, ".")
        assert result.exit_code == 2
        assert "bogus" in result.output
