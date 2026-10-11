# Usage

The command name is `confl` (the PyPI package is `conflint`), so both of these
work after installing into your environment:

```console
confl --help
python -m conflint --help
```

## `confl check`

Lint the project and report configuration drift.

```text
Usage: confl check [OPTIONS] [PATHS]...

Options:
  --config FILE
  --report [github|json|junit|sarif|text]   repeatable; defaults to `text`
  --fail-level [error|warning|info]          exit non-zero at/above this level
  --fix             Auto-remediate fixable findings (syncs `.env.example`)
  --no-color
  --json            shortcut for `--report json`
  --sarif           shortcut for `--report sarif`
  --github          shortcut for `--report github`
  --output FILE     write the report to a file instead of stdout
```

Positional `PATHS` may be files or directories. Directory arguments keep the
project's default include globs; file arguments narrow discovery to those files.

The exit code is `1` if any finding reaches `--fail-level`, `2` for usage
errors, and a `0` if the project is clean.

## `confl sync`

Regenerate `.env.example` from code + sources. The rewrite is lossless with
respect to comments and grouping — it only inserts keys that were missing and
removes keys that no longer exist.

```text
Usage: confl sync [OPTIONS]

Options:
  --config FILE
  --dry-run       print the would-be `.env.example` to stdout
  --output FILE   write to a custom path (implies a full rewrite)
```

## `confl explain KEY`

Trace one key across the project: every read site, every definition site, and
the documented example. Helpful when a rule fires and you want the full picture.

## `confl rules`

List every rule with its default severity. Add `--json` for machine-readable
output.

## `confl init`

Write a commented template `conflint.toml` in the current directory.
`--force` overwrites an existing file.

## `confl version`

Print the installed version.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | OK — no findings at/above the fail level |
| `1` | Findings at/above the fail level |
| `2` | Usage or configuration error |