"""Sync (`.env.example` regeneration) tests."""

from __future__ import annotations

from conflint.config import load_settings
from conflint.engine import Analyzer
from conflint.sync import build_example, default_example_file


def _top(s):
    return s.splitlines()[:3]


def test_fresh_example(tmp_path, write_files):
    write_files(tmp_path, {"app.py": "import os\na=os.environ['A']\nb=os.getenv('B')\n"})
    settings = load_settings(tmp_path)
    model = Analyzer(settings).collect()
    content = build_example(model, settings)
    assert "A=" in content
    assert "B=" in content


def test_roundtrip_on_existing(tmp_path, write_files):
    write_files(
        tmp_path,
        {
            "app.py": "import os\nx = os.getenv('KEEP')\n",
            ".env.example": "# This comment must survive.\nKEEP=old-value\nSTALE=gone\n",
        },
    )
    settings = load_settings(tmp_path)
    model = Analyzer(settings).collect()
    content = build_example(model, settings)
    assert "# This comment must survive." in content
    assert "KEEP=old-value" in content
    assert "STALE" not in content.splitlines() or "# STALE" in content


def test_default_example_file_existing_wins(tmp_path, write_files):
    write_files(tmp_path, {".env.sample": "A=1\n"})
    settings = load_settings(tmp_path)
    assert default_example_file(tmp_path, settings).name == ".env.sample"


def test_empty_model_renders_header(tmp_path):
    settings = load_settings(tmp_path)
    model = Analyzer(settings).collect()
    content = build_example(model, settings)
    assert content.strip()  # never empty: at least the header comment
