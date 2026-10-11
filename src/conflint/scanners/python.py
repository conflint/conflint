"""Python scanner built on the :mod:`ast` module.

Accurate by construction: we parse the file and recognise the real idioms used
to read configuration, rather than grepping for strings.  Recognised forms:

* ``os.environ["KEY"]``                      -> required, no default
* ``os.environ.get("KEY")``                   -> optional (returns ``None``)
* ``os.environ.get("KEY", "fallback")``       -> optional, default recorded
* ``os.environ.setdefault("KEY", "v")``       -> defines a default
* ``os.getenv("KEY")`` / ``os.getenv("K", "d")``
* ``environ["KEY"]`` / ``getenv("KEY")`` after ``from os import ...``
* aliased imports (``import os as o``, ``from os import environ as env``)

Non-constant keys (``os.environ[name]``) are ignored, because we cannot know the
name statically; conflint favours precision over recall.
"""

from __future__ import annotations

import ast
from pathlib import Path

from conflint.models import Language, Location, Usage
from conflint.scanners.base import Scanner

__all__ = ["PythonScanner"]


class _EnvVisitor(ast.NodeVisitor):
    """Collects environment/config reads from a Python AST."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.usages: list[Usage] = []
        self._os_aliases: set[str] = {"os"}
        self._environ_aliases: set[str] = {"environ"}
        self._getenv_aliases: set[str] = {"getenv"}

    # -- import tracking -------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "os":
                self._os_aliases.add(alias.asname or "os")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "os":
            for alias in node.names:
                if alias.name == "environ":
                    self._environ_aliases.add(alias.asname or "environ")
                elif alias.name == "getenv":
                    self._getenv_aliases.add(alias.asname or "getenv")
        self.generic_visit(node)

    # -- helpers ---------------------------------------------------------
    def _is_environ_expr(self, node: ast.AST) -> str | None:
        """Return a human label if ``node`` refers to the ``os.environ`` mapping."""

        if isinstance(node, ast.Name) and node.id in self._environ_aliases:
            return "environ"
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "environ"
            and isinstance(node.value, ast.Name)
            and node.value.id in self._os_aliases
        ):
            return f"{node.value.id}.environ"
        return None

    def _is_getenv_func(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name) and node.id in self._getenv_aliases:
            return node.id
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "getenv"
            and isinstance(node.value, ast.Name)
            and node.value.id in self._os_aliases
        ):
            return f"{node.value.id}.getenv"
        return None

    @staticmethod
    def _const_str(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _record(
        self,
        name: str,
        node: ast.AST,
        read_via: str,
        *,
        required: bool,
        has_default: bool,
        default: str | None,
    ) -> None:
        self.usages.append(
            Usage(
                name=name,
                location=Location(
                    self.path, getattr(node, "lineno", 0), getattr(node, "col_offset", 0) + 1
                ),
                language=Language.PYTHON,
                read_via=read_via,
                required=required,
                has_default=has_default,
                default=default,
            )
        )

    # -- call handling ---------------------------------------------------
    def visit_Call(self, node: ast.Call) -> None:
        # os.getenv("X"[, default])
        getenv = self._is_getenv_func(node.func)
        if getenv and node.args:
            key = self._const_str(node.args[0])
            if key is not None:
                self._record_call_default(key, node, f"{getenv}()")
        else:
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in {"get", "setdefault", "pop"}:
                environ_label = self._is_environ_expr(func.value)
                if environ_label and node.args:
                    key = self._const_str(node.args[0])
                    if key is not None:
                        if func.attr == "setdefault":
                            self._record(
                                key,
                                node,
                                f"{environ_label}.setdefault()",
                                required=False,
                                has_default=True,
                                default=self._const_str(node.args[1])
                                if len(node.args) > 1
                                else None,
                            )
                        else:
                            self._record_call_default(key, node, f"{environ_label}.{func.attr}()")
        self.generic_visit(node)

    def _record_call_default(self, key: str, node: ast.Call, read_via: str) -> None:
        if len(node.args) >= 2 or any(kw.arg in {"default", "key"} for kw in node.keywords):
            default_node: ast.AST | None = None
            if len(node.args) >= 2:
                default_node = node.args[1]
            else:
                for kw in node.keywords:
                    if kw.arg in {"default", "key"}:
                        default_node = kw.value
            default = self._const_str(default_node) if default_node is not None else None
            self._record(
                key,
                node,
                read_via,
                required=False,
                has_default=True,
                default=default if default is not None else "<dynamic>",
            )
        else:
            self._record(key, node, read_via, required=False, has_default=False, default=None)

    # -- subscript handling ----------------------------------------------
    def visit_Subscript(self, node: ast.Subscript) -> None:
        label = self._is_environ_expr(node.value)
        if label:
            key = self._const_str(node.slice)
            if key is not None:
                self._record(
                    key,
                    node,
                    f"{label}[]",
                    required=True,
                    has_default=False,
                    default=None,
                )
        self.generic_visit(node)


class PythonScanner(Scanner):
    """Static scanner for ``.py`` files."""

    name = "python"
    language = Language.PYTHON
    extensions = (".py", ".pyi")

    def scan(self, path: Path, text: str) -> list[Usage]:
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            # A file that does not parse contributes nothing rather than
            # aborting the run; it is flagged elsewhere by ordinary tooling.
            return []
        visitor = _EnvVisitor(path)
        visitor.visit(tree)
        return visitor.usages
