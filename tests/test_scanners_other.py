"""Tests for the Go and Ruby scanners."""

from __future__ import annotations

from pathlib import Path

from conflint.scanners.go import GoScanner
from conflint.scanners.ruby import RubyScanner


class TestGoScanner:
    path = Path("main.go")

    def _scan(self, text: str):
        return GoScanner().scan(self.path, text)

    def _by_name(self, usages):
        return {u.name: u for u in usages}

    def test_getenv(self):
        usages = self._by_name(self._scan('h := os.Getenv("HOST")\n'))
        assert "HOST" in usages
        assert usages["HOST"].required is False

    def test_lookupenv_notes(self):
        usage = self._by_name(self._scan('v, ok := os.LookupEnv("PORT")\n'))["PORT"]
        assert "presence-checked" in usage.notes

    def test_setenv_notes(self):
        usage = self._by_name(self._scan('os.Setenv("FOO", "bar")\n'))["FOO"]
        assert "write" in usage.notes

    def test_line_number(self):
        usages = self._scan('\nos.Getenv("ZZ")\n')
        assert usages[0].location.line == 2


class TestRubyScanner:
    path = Path("config.rb")

    def _scan(self, text: str):
        return RubyScanner().scan(self.path, text)

    def _by_name(self, usages):
        return {u.name: u for u in usages}

    def test_subscript(self):
        usages = self._by_name(self._scan('ENV["HOST"]\n'))
        assert "HOST" in usages
        assert usages["HOST"].required is False

    def test_fetch_required(self):
        usage = self._by_name(self._scan('ENV.fetch("HOST")\n'))["HOST"]
        assert usage.required is True

    def test_fetch_with_default(self):
        usage = self._by_name(self._scan("ENV.fetch('HOST', 'localhost')\n"))["HOST"]
        assert usage.has_default is True
        assert usage.default == "localhost"

    def test_subscript_default(self):
        usage = self._by_name(self._scan('x = ENV["HOST"] || "localhost"\n'))["HOST"]
        assert usage.default == "localhost"
