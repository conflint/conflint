"""Tests for the JavaScript/TypeScript scanner."""

from __future__ import annotations

from pathlib import Path

from conflint.scanners.javascript import JavaScriptScanner

PATH = Path("server.ts")


def _scan(text: str):
    return JavaScriptScanner().scan(PATH, text)


def _by_name(usages):
    return {u.name: u for u in usages}


def test_process_env_dotted():
    usages = _by_name(_scan("const host = process.env.API_HOST;\n"))
    assert "API_HOST" in usages
    assert usages["API_HOST"].has_default is False


def test_process_env_bracket():
    usages = _by_name(_scan('const p = process.env["PORT"];\n'))
    assert "PORT" in usages


def test_import_meta_env():
    usages = _by_name(_scan("const v = import.meta.env.VITE_API;\n"))
    assert "VITE_API" in usages


def test_bun_env():
    usages = _by_name(_scan("export default { port: Bun.env.PORT };\n"))
    assert "PORT" in usages


def test_deno_env_get():
    usages = _by_name(_scan("const token = Deno.env.get('TOKEN');\n"))
    assert "TOKEN" in usages


def test_destructuring():
    usages = _by_name(_scan("const { A, B: b, C = 'x' } = process.env;\n"))
    assert {"A", "B", "C"} <= set(usages)
    assert usages["A"].has_default is False
    assert usages["C"].has_default is True
    assert usages["C"].default == "x"


def test_inline_default_question_mark():
    usage = _by_name(_scan('const x = process.env.LEVEL ?? "info";\n'))["LEVEL"]
    assert usage.has_default is True
    assert usage.default == "info"


def test_inline_default_or():
    usage = _by_name(_scan("const x = process.env.HOST || 'localhost';\n"))["HOST"]
    assert usage.default == "localhost"


def test_line_number():
    usages = _scan("\n\n  const a = process.env.X;\n")
    assert usages[0].location.line == 3


def test_no_false_positive_on_plain_object():
    usages = _scan("const env = { HOST: 'x' };\n")
    assert usages == []
