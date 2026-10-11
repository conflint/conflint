# Contributing to conflint

Thanks for your interest! Here is how to set up the project, run the checks
that CI runs, and get a change merged.

## Environment

conflint supports Python 3.9+. Create a virtual environment and install the
development extras:

```console
python -m venv .venv
.venv\\Scripts\\activate        # Windows
source .venv/bin/activate       # macOS / Linux
pip install -e ".[dev]"
```

## Run the checks

All of these must pass before a merge. They mirror the CI workflow:

```console
ruff check src tests        # linter
ruff format --check src tests
mypy src                    # strict type checking
pytest                      # test suite
```

- `ruff format src tests` will reformat; run `ruff check --fix` to auto-fix
  most lint issues.
- Do not commit secrets, and do not bump the version in the same PR as a
  feature. Versions come from git tags (`hatch-vcs`), see
  [Packaging](#packaging).

## Where things live

| Path | What it is |
| --- | --- |
| `src/conflint/scanners/` | Language scanners (Python, JS, Go, Ruby) |
| `src/conflint/sources/` | Config file parsers (dotenv, compose, GH Actions, k8s, terraform) |
| `src/conflint/rules/` | The CL001–CL009 rules |
| `src/conflint/reporters/` | Output formats (text, json, sarif, github, junit) |
| `src/conflint/engine.py` | Orchestration: discovery → scan → parse → rules |
| `src/conflint/cli.py` | The `confl` command-line interface |
| `tests/` | The test suite |

### Adding a rule

1. Create `src/conflint/rules/<name>.py` with a `Rule` subclass.
2. Register it under `[project.entry-points."conflint.rules"]` in
   `pyproject.toml` (next free `CLxxx` id).
3. Add a test in `tests/test_rules.py`.
4. Document it in `docs/rules.md`.

### Adding a scanner or source

Same pattern: subclass `Scanner` / `ConfigSource`, register the entry point in
`pyproject.toml`, add tests, update docs.

## Tests

The suite lives in `tests/` and uses plain `pytest` with `tmp_path` for
isolation. Run a single file with:

```console
pytest tests/test_sources.py -q
```

## Pre-commit

A `.pre-commit-config.yaml` is provided (ruff + mypy). Using it is optional —
CI enforces the same checks. The mirror `rev`s in that file are pinned
manually; bump them in the same PR where you bump `ruff`/`mypy` in the dev
extras. To install:

```console
pip install pre-commit
pre-commit install
```

## Packaging

Versions are derived from git tags by `hatch-vcs`. To build locally:

```console
python -m build
python -m twine check dist/*
```

## Pull requests

- Keep changes focused; separate commits for separate concerns.
- Update `CHANGELOG.md` (Unreleased section) for user-visible changes.
- Make sure the full check suite passes locally before pushing.

## Reporting issues

Use the GitHub issue tracker. Include the `confl --version` output and a
minimal reproducer if possible.