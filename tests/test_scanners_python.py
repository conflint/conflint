"""Tests for the Python AST scanner."""

from __future__ import annotations

from pathlib import Path

from conflint.scanners.python import PythonScanner

PATH = Path("app.py")


def _scan(text: str):
    return PythonScanner().scan(PATH, text)


def _by_name(usages):
    return {u.name: u for u in usages}


def test_subscript_is_required():
    usages = _scan("import os\nx = os.environ['DB_URL']\n")
    usage = _by_name(usages)["DB_URL"]
    assert usage.required is True
    assert usage.has_default is False
    assert usage.read_via == "os.environ[]"


def test_getenv_without_default():
    usage = _by_name(_scan("import os\nx=os.getenv('PORT')\n"))["PORT"]
    assert usage.required is False
    assert usage.has_default is False
    assert usage.default is None


def test_getenv_with_default():
    usage = _by_name(_scan("import os\nx=os.getenv('PORT', '8080')\n"))["PORT"]
    assert usage.has_default is True
    assert usage.default == "8080"


def test_environ_get_default():
    usage = _by_name(_scan("import os\nx=os.environ.get('HOST', 'localhost')\n"))["HOST"]
    assert usage.default == "localhost"


def test_from_os_import_aliases():
    usages = _by_name(
        _scan("from os import getenv\nfrom os import environ as env\na=getenv('A')\nb=env['B']\n")
    )
    assert usages["A"].read_via == "getenv()"
    assert usages["B"].required is True


def test_import_os_as_alias():
    usages = _by_name(_scan("import os as o\nx=o.getenv('C')\n"))
    assert "C" in usages


def test_setdefault_records_default():
    usages = _by_name(_scan("import os\nos.environ.setdefault('D', 'dd')\n"))
    assert usages["D"].has_default is True
    assert usages["D"].default == "dd"


def test_dynamic_subscript_ignored():
    usages = _scan("import os\nk = 'X'\nv = os.environ[k]\n")
    assert usages == []


def test_other_environment_libraries_ignored():
    # pydantic settings / configparser should not match.
    usages = _scan("import configparser\nc = configparser['X']\n")
    assert usages == []


def test_syntax_error_yields_empty():
    usages = _scan("import os\ndef broken(:\n")
    assert usages == []


def test_multiple_reads_same_key():
    usages = _scan("import os\na=os.environ['K']\nb=os.environ['K']\n")
    assert [u.name for u in usages] == ["K", "K"]
    assert usages[0].location.line == 2
    assert usages[1].location.line == 3


def test_line_numbers():
    usages = _scan("import os\n\n\nx = os.getenv('N')\n")
    assert usages[0].location.line == 4
