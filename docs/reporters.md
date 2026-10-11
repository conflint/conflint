# Reporters

Select a reporter with `confl check --report NAME` (repeatable), with the
`--json` / `--sarif` / `--github` shortcuts, or through the `reporters` setting.
When `--output FILE` is given with a single reporter, the report is written to
the file instead of stdout.

| Name | Purpose |
| --- | --- |
| `text` | Rich terminal output (default), grouped by file then severity |
| `json` | Stable JSON schema for scripts and dashboards |
| `sarif` | SARIF 2.1.0 for GitHub code scanning, CodeQL, Azure Pipelines, GitLab |
| `github` | GitHub Actions workflow-command annotations |
| `junit` | JUnit XML for Jenkins dashboards and `gha`-style consumers |

## JSON schema (v1)

```json
{
  "schema_version": "1.0",
  "conflint_version": "0.1.0",
  "root": "/home/me/app",
  "summary": {
    "files_scanned": 42,
    "usages": 173,
    "entries": 58,
    "duration_ms": 1240.0,
    "counts": { "error": 2, "warning": 1, "info": 0 }
  },
  "sources": [
    {
      "name": "dotenv",
      "files": [".env", ".env.local"],
      "entries": 8,
      "is_example": false
    }
  ],
  "findings": [
    {
      "rule": "CL001",
      "severity": "error",
      "message": "'DATABASE_URL' is read in code but not defined in any configuration source",
      "key": "DATABASE_URL",
      "location": { "path": "app/main.py", "line": 12, "column": 5 },
      "help": "Add it to your .env (then run `confl sync` to refresh .env.example)",
      "fixable": false,
      "data": {}
    }
  ]
}
```

## SARIF

`confl check --sarif` emits a single run with a `results` array per finding,
`locations` pointing at the offending file/line, and rule metadata under
`tool.driver.rules`. Wheel `error`/`warning`/`info` findings map to SARIF
`error`/`warning`/`note` levels.