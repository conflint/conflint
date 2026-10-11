"""Discovery tests: include/exclude globs and gitignore semantics."""

from __future__ import annotations

from conflint.config import load_settings
from conflint.discovery import discover


class TestDiscovery:
    def test_config_file_bypasses_gitignore(self, tmp_path, write_files):
        write_files(
            tmp_path,
            {
                ".gitignore": ".env\n",
                ".env": "A=1\n",
                "app.py": "print(1)\n",
            },
        )
        result = discover(tmp_path, load_settings(tmp_path), config_globs=(".env",))
        code = {p.name for p in result.code_files}
        config = {p.name for p in result.config_files}
        assert "app.py" in code
        assert ".env" not in code
        assert ".env" in config

    def test_exclude_patterns(self, tmp_path, write_files):
        write_files(
            tmp_path,
            {
                "a.py": "x=1\n",
                "b.py": "y=2\n",
                "nested/deep.py": "z=3\n",
            },
        )
        settings = load_settings(tmp_path, overrides={"exclude": ["b.py", "nested/**"]})
        result = discover(tmp_path, settings)
        assert {p.name for p in result.code_files} == {"a.py"}

    def test_nested_file_bypasses_gitignore(self, tmp_path, write_files):
        write_files(
            tmp_path,
            {
                ".gitignore": "sub/.env\n",
                "sub/.env": "A=1\n",
            },
        )
        result = discover(tmp_path, load_settings(tmp_path), config_globs=("**/.env",))
        assert {p.name for p in result.config_files} == {".env"}


class TestIncludes:
    def test_include_restricts_code_files(self, tmp_path, write_files):
        write_files(
            tmp_path,
            {
                "src/a.py": "x=1\n",
                "tests/b.py": "y=2\n",
            },
        )
        settings = load_settings(tmp_path, overrides={"include": ["src/**"]})
        result = discover(tmp_path, settings)
        rel = {str(p.relative_to(tmp_path)).replace("\\", "/") for p in result.code_files}
        assert rel == {"src/a.py"}
