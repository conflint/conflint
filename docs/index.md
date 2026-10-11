# conflint

**Code-aware configuration linting.**

Find every env var, config key and secret your app *actually* reads, then
reconcile it against `.env`, CI, Docker, Kubernetes and Terraform — before it
breaks prod.

```console
pip install conflint
confl check
```

## Why conflint?

Most "works on my machine" disasters are configuration disasters:

- A teammate deleted a key from `.env` that your code still **requires**.
- The CI workflow never defines `DATABASE_URL`, so the app crashes at **deploy**,
  not at commit.
- `DB_HOST` vs `DBHOST` — a typo no linter catches, because the linter doesn't
  read your code.
- A real API key committed inside a `.env`.

`.env` linters validate a file against a **schema you write by hand**. conflint
reads the **actual source code** to learn what your app needs, then reconciles it
against every place that value should exist.

## Quick start

```bash
pip install conflint
```

From your project root:

```bash
confl check                  # lint the whole project
confl sync                   # regenerate an accurate .env.example
confl explain DB_HOST        # who reads DB_HOST? where is it defined?
```

Example output:

```text
conflint  checked 42 files (173 config reads, 58 definitions) in 1.24s

app/main.py
  CL001 error: 'DATABASE_URL' is read in code but not defined in any configuration source:12
    hint: Add it to your .env (then run `confl sync` to refresh .env.example)
  CL003 warning: 'DBHOST' is undefined but resembles 'DB_HOST' (distance 1):45
    hint: Did you mean 'DB_HOST'?
docker-compose.yml
  CL004 error: 'POSTGRES_PASSWORD' looks like a committed secret

42 files checked - 2 errors, 1 warning, 0 infos
```

## What gets scanned

| Language | Files | Recognised reads |
| --- | --- | --- |
| Python | `.py`, `.pyi` (AST) | `os.environ[...]`, `os.environ.get`, `os.getenv` (+ aliases) |
| JS/TS | `.js`, `.ts`, `.jsx` ... | `process.env`, `import.meta.env`, `Bun.env`, `Deno.env.get`, destructuring |
| Go | `.go` | `os.Getenv`, `os.LookupEnv`, `os.Setenv` |
| Ruby | `.rb` | `ENV[...]`, `ENV.fetch` |

## Configuration sources

| Source | Finds |
| --- | --- |
| dotenv | `.env`, `.env.local`, `.env.example`, ... |
| docker-compose | `services.*.environment` (list & map styles) |
| github-actions | `env:` maps in `.github/workflows/*` |
| kubernetes | container `env`, `ConfigMap.data`, `Secret.data` |
| terraform | `variable ""`, `.tfvars`, `environment = {}` blocks |

Configuration files are located directly and **bypass `.gitignore`** (a `.env`
is often gitignored on purpose). Source code is walked **respecting** `.gitignore`
and the configured include/exclude globs.

## Docs

- [Usage](usage.md) — the `confl` command-line reference.
- [Rules](rules.md) — every rule (CL001–CL009) and when it fires.
- [Configuration](configuration.md) — `conflint.toml` and `[tool.conflint]`.
- [Reporters](reporters.md) — text, JSON, SARIF, GitHub, JUnit.
- [Plugins](plugins.md) — third-party scanners, sources and rules.
- [Reference](reference.md) — the public API.