"""The analysis engine.

Pipeline:

1. instantiate selected scanners / sources / rules
2. discover files (code respects ``.gitignore``; config sources bypass it)
3. scan code -> usages
4. parse config files -> entries
5. mark example entries by file name
6. build the reconciled :class:`~conflint.models.Config`
7. run rules, apply per-rule severity overrides, drop disabled rules
8. assemble a :class:`~conflint.models.Report`
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from pathlib import Path

from conflint.config import Settings
from conflint.discovery import discover
from conflint.exceptions import RuleError
from conflint.models import Config, Entry, Finding, Report, SourceSummary, Usage
from conflint.registry import get_rules, get_scanners, get_sources
from conflint.sources import ConfigSource
from conflint.utils import read_text

logger = logging.getLogger("conflint.engine")

__all__ = ["Analyzer", "analyze"]

# Order matters: files that could be claimed by several sources (YAML files,
# particularly) are parsed by the first matching source.
_SOURCE_PRIORITY = ("dotenv", "github-actions", "docker-compose", "kubernetes", "terraform")


class Analyzer:
    """Runs one analysis pass over a project."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._last_file_count = 0
        self._scanners = [
            scanner
            for scanner in get_scanners()
            if not settings.scanners or scanner.name in settings.scanners
        ]
        self._sources = [
            source
            for source in get_sources()
            if not settings.sources or source.name in settings.sources
        ]

        def _source_key(source: ConfigSource) -> int:
            try:
                return _SOURCE_PRIORITY.index(source.name)
            except ValueError:
                return len(_SOURCE_PRIORITY)

        self._sources.sort(key=_source_key)
        self._rules = get_rules()

    # -- public API ------------------------------------------------------
    def collect(self) -> Config:
        """Run discovery, scanning and parsing; return the reconciled model."""

        settings = self.settings

        config_globs: list[str] = []
        for source in self._sources:
            config_globs.extend(source.candidate_globs())

        discovered = discover(settings.root, settings, config_globs=config_globs)
        self._last_file_count = len(discovered.all)

        usages = self._scan_code(discovered.code_files)
        entries = self._parse_sources(discovered.config_files)
        entries = self._mark_examples(entries)

        return Config(
            root=settings.root,
            usages=usages,
            entries=entries,
            sources=self._summarize(entries),
            settings={},
        )

    def run(self) -> Report:
        started = time.perf_counter()
        model = self.collect()

        findings = self._run_rules(model)
        self._apply_overrides(findings)

        duration_ms = (time.perf_counter() - started) * 1000.0
        return Report(
            findings=findings,
            usages=len(model.usages),
            entries=len(model.entries),
            files_scanned=self._last_file_count,
            duration_ms=duration_ms,
            sources=model.sources,
        )

    # -- pipeline steps --------------------------------------------------
    def _scan_code(self, files: Sequence[Path]) -> list[Usage]:
        usages: list[Usage] = []
        for path in files:
            for scanner in self._scanners:
                if not scanner.handles(path):
                    continue
                try:
                    text = read_text(path)
                except OSError as exc:  # pragma: no cover - filesystem
                    logger.warning("skipping unreadable file %s: %s", path, exc)
                    continue
                usages.extend(scanner.scan(path, text))
                break
        return usages

    def _parse_sources(self, files: Sequence[Path]) -> list[Entry]:
        # A file is parsed (at most once) by the highest-priority source that
        # claims it (YAML files, for instance, can match several sources).
        parsed: set[str] = set()
        entries: list[Entry] = []
        for source in self._sources:
            for path in files:
                if str(path) in parsed or not source.matches(path):
                    continue
                try:
                    text = read_text(path)
                except OSError as exc:  # pragma: no cover - filesystem
                    logger.warning("skipping unreadable config %s: %s", path, exc)
                    continue
                entries.extend(source.parse(path, text))
                parsed.add(str(path))
        return entries

    def _mark_examples(self, entries: list[Entry]) -> list[Entry]:
        example_names = {name.lower() for name in self.settings.example_files}
        for entry in entries:
            if entry.location.path.name.lower() in example_names:
                entry.is_example = True
        return entries

    def _run_rules(self, model: Config) -> list[Finding]:
        findings: list[Finding] = []
        for rule_id, rule in self._rules.items():
            if self.settings.is_disabled(rule_id):
                continue
            try:
                findings.extend(rule.check(model, self.settings))
            except Exception as exc:
                raise RuleError(f"rule {rule_id} failed: {exc}") from exc
        return findings

    def _apply_overrides(self, findings: list[Finding]) -> None:
        for finding in findings:
            override = self.settings.severity_for(finding.rule_id)
            if override is not None:
                finding.severity = override

    @staticmethod
    def _summarize(entries: list[Entry]) -> list[SourceSummary]:
        grouped: dict[str, SourceSummary] = {}
        for entry in entries:
            summary = grouped.setdefault(entry.source, SourceSummary(name=entry.source))
            summary.entries += 1
            if entry.location.path not in summary.files:
                summary.files = (*summary.files, entry.location.path)
        return sorted(grouped.values(), key=lambda s: s.name)


def analyze(settings: Settings, *, previous: Analyzer | None = None) -> Report:
    """Convenience wrapper around :class:`Analyzer`."""

    if previous is not None:
        # Kept symmetric with a session-based API for future caching hooks.
        return previous.run()
    return Analyzer(settings).run()
