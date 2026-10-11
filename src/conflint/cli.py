"""conflint command-line interface.

The command name is :program:`confl` (the PyPI package is ``conflint``)::

    pip install conflint
    confl check
    confl sync
    confl explain DB_HOST
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import click

from conflint.__about__ import __version__
from conflint.config import Settings, load_settings
from conflint.engine import Analyzer
from conflint.exceptions import ConflintError, ExitCode
from conflint.registry import get_rules
from conflint.reporters import GithubReporter, JsonReporter, JunitReporter, SarifReporter, TextReporter
from conflint.sync import build_example, default_example_file
from conflint.utils import read_text

logger = logging.getLogger("conflint.cli")

__all__ = ["main"]

_REPORTERS = {
    "text": TextReporter,
    "json": JsonReporter,
    "sarif": SarifReporter,
    "github": GithubReporter,
    "junit": JunitReporter,
}


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="confl", message="%(prog)s %(version)s")
def main() -> None:
    """conflint - code-aware config linter.

    Find the env vars, config keys and secrets your app *actually* reads, then
    reconcile them against .env, CI, Docker, Kubernetes and Terraform.
    """


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------
@main.command()
@click.argument("paths", nargs=-1, type=click.Path())
@click.option("--config", "config_path", type=click.Path(dir_okay=False))
@click.option("--report", "report_flags", multiple=True, type=click.Choice(sorted(_REPORTERS)))
@click.option("--fail-level", type=click.Choice(["error", "warning", "info"]))
@click.option("--fix", is_flag=True, help="Auto-remediate fixable findings.")
@click.option("--no-color", "no_color", is_flag=True)
@click.option("--json", "as_json", is_flag=True, hidden=False)
@click.option("--sarif", "as_sarif", is_flag=True)
@click.option("--github", "as_github", is_flag=True)
@click.option("--output", type=click.Path(dir_okay=False), help="Write the report to a file.")
def check(
    paths: Tuple[str, ...],
    config_path: Optional[str],
    report_flags: Tuple[str, ...],
    fail_level: Optional[str],
    fix: bool,
    no_color: bool,
    as_json: bool,
    as_sarif: bool,
    as_github: bool,
    output: Optional[str],
) -> int:
    """Lint the project and report configuration drift."""

    root = _resolve_root(paths)
    try:
        settings = load_settings(
            root,
            config_path=Path(config_path) if config_path else None,
            overrides=_build_overrides(paths, fail_level, no_color),
        )
    except ConflintError as exc:
        click.echo(f"confl: {exc}", err=True)
        return ExitCode.USAGE

    reporter_classes = _select_reporters(settings, report_flags, as_json, as_sarif, as_github)
    if not reporter_classes:
        click.echo("confl: no reporters selected", err=True)
        return ExitCode.USAGE

    try:
        analyzer = Analyzer(settings)
        if fix:
            _autofix(analyzer, settings)
        report = analyzer.run()
    except ConflintError as exc:
        click.echo(f"confl: {exc}", err=True)
        return ExitCode.INTERNAL

    _emit(report_classes, report, settings, output)

    if report.has_findings_at_or_above(settings.fail_level):
        return ExitCode.FINDINGS
    return ExitCode.OK


# --------------------------------------------------------------------------
# sync
# --------------------------------------------------------------------------
@main.command()
@click.option("--config", "config_path", type=click.Path(dir_okay=False))
@click.option("--dry-run", is_flag=True, help="Print the generated file without writing.")
@click.option("--output", type=click.Path(dir_okay=False), help="Example file to write/update.")
def sync(config_path: Optional[str], dry_run: bool, output: Optional[str]) -> int:
    """Regenerate the .env.example from code + config sources."""

    root = Path.cwd()
    try:
        settings = load_settings(root, config_path=Path(config_path) if config_path else None)
        model = Analyzer(settings).collect()
    except ConflintError as exc:
        click.echo(f"confl: {exc}", err=True)
        return ExitCode.USAGE

    content = build_example(model, settings)
    if dry_run:
        click.echo(content, nl=False)
        return ExitCode.OK

    target = Path(output) if output else default_example_file(settings.root, settings)
    changed = target.is_file() and read_text(target) == content
    try:
        target.write_text(content, encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem dependent
        click.echo(f"confl: cannot write {target}: {exc}", err=True)
        return ExitCode.INTERNAL
    click.echo(("unchanged: " if changed else "updated: ") + str(target))
    return ExitCode.OK


# --------------------------------------------------------------------------
# explain
# --------------------------------------------------------------------------
@main.command("explain")
@click.argument("name")
@click.option("--config", "config_path", type=click.Path(dir_okay=False))
def explain(name: str, config_path: Optional[str]) -> int:
    """Show where a configuration value is used and defined."""

    root = Path.cwd()
    try:
        settings = load_settings(root, config_path=Path(config_path) if config_path else None)
        analyzer = Analyzer(settings)
        model = analyzer.collect()
    except ConflintError as exc:
        click.echo(f"confl: {exc}", err=True)
        return ExitCode.USAGE

    usages = model.usages_by_name().get(name, [])
    entries = model.entries_by_name().get(name, [])
    if not usages and not entries:
        click.echo(f"confl: '{name}' is not used or defined anywhere.", err=True)
        return ExitCode.FINDINGS

    click.echo(f"[bold]{name}[/bold]")
    if usages:
        click.echo(f"  read at {len(usages)} place(s):")
        seen = set()
        for usage in usages:
            line = str(usage.location.relative_to(model.root))
            if line in seen:
                continue
            seen.add(line)
            detail = f"  - {line}  (via {usage.read_via or '?'}"
            if usage.has_default:
                detail += f", default={usage.default!r})"
            else:
                detail += ")"
            click.echo(detail)
    if entries:
        click.echo(f"  defined in {len(entries)} place(s):")
        for entry in entries:
            click.echo(
                f"  - {entry.location.relative_to(model.root)}  "
                f"({entry.source}, value={entry.value!r}, example={entry.is_example})"
            )
    else:
        click.echo("  not defined in any configuration source")
    return ExitCode.OK


# --------------------------------------------------------------------------
# rules / init / version
# --------------------------------------------------------------------------
@main.command("rules")
@click.option("--json", "as_json", is_flag=True)
def rules(as_json: bool) -> int:
    """List every rule with its default severity."""

    items = []
    for rule_id, rule in get_rules().items():
        items.append(
            {
                "id": rule.id,
                "name": rule.name,
                "severity": rule.severity.value,
                "description": rule.description,
                "fixable": rule.fixable,
            }
        )
    if as_json:
        import json as _json

        click.echo(_json.dumps(items, indent=2))
        return ExitCode.OK

    click.echo(f"{'Rule':<8} {'Severity':<9} {'Name':<16} Description")
    for item in items:
        click.echo(
            f"{item['id']:<8} {item['severity']:<9} {item['name']:<16} {item['description']}"
        )
    return ExitCode.OK


@main.command("init")
@click.option("--force", is_flag=True, help="Overwrite an existing conflint.toml.")
def init(force: bool) -> int:
    """Write a template conflint.toml in the current directory."""

    target = Path.cwd() / "conflint.toml"
    if target.exists() and not force:
        click.echo(f"confl: {target} already exists (use --force to overwrite).", err=True)
        return ExitCode.USAGE
    _TEMPLATE = """\
# conflint configuration - https://github.com/confl/conflint
# Uncomment and adjust:

# [tool.conflint]

# fail-level = "error"              # error | warning | info
# require-example = true            # enforce a populated .env.example

# enable = { CL003 = "error" }      # raise a rule's severity
# disable = ["CL002", "CL009"]      # turn rules off

# ignore-names = ["CI=true", "NODE_ENV=*"]
# ignore-paths = ["scripts/**"]

# sources = ["dotenv", "docker-compose", "github-actions", "kubernetes", "terraform"]
# scanners = ["python", "javascript"]
"""
    try:
        target.write_text(_TEMPLATE, encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        click.echo(f"confl: cannot write {target}: {exc}", err=True)
        return ExitCode.INTERNAL
    click.echo(f"created {target}")
    return ExitCode.OK


@main.command()
def version() -> int:
    """Print the installed version."""

    click.echo(f"confl {__version__}")
    return ExitCode.OK


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _resolve_root(paths: Sequence[str]) -> Path:
    if not paths:
        return Path.cwd()
    first = Path(paths[0])
    if first.is_dir():
        return first.resolve()
    return first.parent.resolve()


def _build_overrides(
    paths: Sequence[str],
    fail_level: Optional[str],
    no_color: bool,
) -> Dict:
    overrides: Dict = {}
    if paths:
        includes = []
        for raw in paths:
            path = Path(raw)
            if path.is_dir():
                includes.append(str(path) + "/**/*")
            else:
                includes.append(raw.replace("\\", "/"))
        overrides["include"] = includes
    if fail_level:
        overrides["fail-level"] = fail_level
    if no_color:
        overrides["color"] = False
    return overrides


def _select_reporters(
    settings: Settings,
    flags: Sequence[str],
    as_json: bool,
    as_sarif: bool,
    as_github: bool,
) -> List:
    chosen: List[str] = []
    if as_json:
        chosen.append("json")
    if as_sarif:
        chosen.append("sarif")
    if as_github:
        chosen.append("github")
    if not chosen:
        chosen.extend(flags)
    if not chosen:
        chosen.extend(settings.reporters)
    unique = list(dict.fromkeys(chosen))
    return [_REPORTERS[name] for name in unique if name in _REPORTERS]


def _emit(reporter_classes, report, settings: Settings, output: Optional[str]) -> None:
    rendered = [(cls.name, cls().render(report, settings)) for cls in reporter_classes]
    if output is not None and len(rendered) == 1:
        path = Path(output)
        try:
            path.write_text(rendered[0][1], encoding="utf-8")
        except OSError as exc:  # pragma: no cover
            click.echo(f"confl: cannot write {path}: {exc}", err=True)
        return
    for _, text in rendered:
        click.echo(text, nl=text.endswith("\n"))


def _autofix(analyzer: Analyzer, settings: Settings) -> None:
    """Apply safe, lossless auto-fixes.

    Currently resolves CL009 (undocumented keys) by rewriting the example file.
    All fixes are deterministic and never touch real configuration values.
    """

    if not settings.require_example:
        return
    model = analyzer.collect()
    content = build_example(model, settings)
    target = default_example_file(settings.root, settings)
    if target.is_file() and read_text(target) == content:
        return
    target.write_text(content, encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    main()