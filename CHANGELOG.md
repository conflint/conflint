# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Code-aware configuration linter with scanners for Python, JavaScript, Go and
  Ruby.
- Configuration sources: dotenv, docker-compose, GitHub Actions, Kubernetes and
  Terraform.
- Nine rules (CL001–CL009) covering missing, unused, misspelled, secret,
  drift, empty, duplicate, weak and undocumented values.
- Reporters: text, JSON, SARIF, GitHub annotations and JUnit.
- `confl` CLI with `check`, `sync` (example-file generator), `explain`, `init`
  and `rules` commands.
- `conflint.toml` / `[tool.conflint]` configuration with CLI overrides.
- Plugin entry points for third-party scanners, sources and rules.
- Test suite (135 tests), strict mypy typing, ruff linting/formatting, CI
  (GitHub Actions) and pre-commit hooks.