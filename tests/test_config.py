"""Configuration loading tests."""

from __future__ import annotations

import pytest

from conflint.config import load_settings
from conflint.exceptions import ConfigError
from conflint.models import Severity


def test_defaults(tmp_path):
    settings = load_settings(tmp_path)
    assert settings.fail_level == Severity.ERROR
    assert settings.require_example is True
    assert settings.include and settings.exclude


def test_pyproject_nested(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.conflint]\nfail-level = "warning"\ndisable = ["CL001"]\n',
        encoding="utf-8",
    )
    settings = load_settings(tmp_path)
    assert settings.fail_level == Severity.WARNING
    assert "CL001" in settings.disable


def test_conflint_toml(tmp_path):
    (tmp_path / "conflint.toml").write_text(
        "require-example = false\n",
        encoding="utf-8",
    )
    settings = load_settings(tmp_path)
    assert settings.require_example is False


def test_unknown_key_rejected(tmp_path):
    (tmp_path / "conflint.toml").write_text("wat = 1\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(tmp_path)


def test_unknown_nested_key(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.conflint]\nbogus-option = 1\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError):
        load_settings(tmp_path)


def test_severity_coercion(tmp_path):
    (tmp_path / "conflint.toml").write_text('fail-level = "nope"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(tmp_path)


def test_enable_table(tmp_path):
    (tmp_path / "conflint.toml").write_text(
        'enable = { CL003 = "error", CL009 = "warning" }\n',
        encoding="utf-8",
    )
    settings = load_settings(tmp_path)
    assert settings.severity_for("CL003") == Severity.ERROR
    assert settings.severity_for("CL009") == Severity.WARNING
    assert settings.severity_for("CL001") is None


def test_cli_override_wins(tmp_path):
    (tmp_path / "conflint.toml").write_text('fail-level = "info"\n', encoding="utf-8")
    settings = load_settings(tmp_path, overrides={"fail-level": "error"})
    assert settings.fail_level == Severity.ERROR


def test_explicit_config_path(tmp_path, tmp_path_factory):
    other = tmp_path_factory.mktemp("cfg") / "special.toml"
    other.write_text('sources = ["dotenv"]\n', encoding="utf-8")
    settings = load_settings(tmp_path, config_path=other)
    assert settings.sources == ("dotenv",)


def test_ignore_name_partial(tmp_path):
    settings = load_settings(tmp_path)
    settings.ignore_names = ("CI*",)
    assert settings.is_name_ignored("CI") is True
    assert settings.is_name_ignored("NODE_ENV") is False
