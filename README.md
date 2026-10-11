<div align="center">

# conflint

**Code-aware configuration linting.**  
Find every env var, config key and secret your app *actually* reads, then reconcile
it against `.env`, CI, Docker, Kubernetes and Terraform — **before it breaks prod**.

`pip install conflint` · `confl check` · [`conflint` on PyPI](https://pypi.org/project/conflint)

</div>

---

## Why conflint?

Most "works on my machine" disasters are configuration disasters:

- A teammate deleted a key from `.env` that your code still **requires**.
- The CI workflow never defines `DATABASE_URL`, so the app crashes at **deploy**, not at commit.
- `DB_HOST` vs `DBHOST` — the typo that no linter catches because your linter doesn't read your code.
- A real API key sitting in a committed `.env`.

`.env` linters validate a file against a **schema you write by hand**. conflint reads
the **actual source code** to learn the truth about what your app needs, then
reconciles it against **every** place that value should exist.

## Quick start

```bash
pip install conflint
```

```bash
# From your project root:
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

## Commands

| Command               | Purpose                                                            |
| --------------------- | ------------------------------------------------------------------ |
| `confl check`         | Run all rules and exit `1` if anything reaches your fail level.     |
| `confl check --fix`   | Auto-remediate fixable findings (currently: syncs `.env.example`).  |
| `confl sync`          | Regenerate `.env.example` from code + sources (lossless rewrite).   |
| `confl explain KEY`   | Trace one key: every read site and every definition site.           |
| `confl rules`         | List all rules with their default severity.                         |
| `confl init`          | Write a template `conflint.toml`.                                   |
| `confl version`       | Print the installed version.                                        |

## Rules

| Rule  | Name          | Default   | Meaning                                                            |
| ----- | ------------- | --------- | ------------------------------------------------------------------ |
| CL001 | missing       | error     | read in code, defined nowhere                                      |
| CL002 | unused        | warning   | defined for real, never read by code                               |
| CL003 | typo          | warning   | undefined name is one edit away from a known one                   |
| CL004 | secret-leak   | error     | high-entropy secret committed in a config source                   |
| CL005 | drift         | error     | documented in `.env.example`, provided by no real source           |
| CL006 | empty-value   | warning   | required value defined but empty                                   |
| CL007 | duplicate     | warning   | defined twice in one file / conflicting values across sources      |
| CL008 | weak-secret   | warning   | secret value equals a weak/default placeholder                     |
| CL009 | undocumented | info      | used or provided, but missing from the example template            |

### What gets scanned

| Language | Files                    | Recognised reads                                            |
| -------- | ------------------------ | ----------------------------------------------------------- |
| Python   | `.py`, `.pyi` (AST)      | `os.environ[...]`, `os.environ.get`, `os.getenv` (+ aliases) |
| JS/TS    | `.js`, `.ts`, `.jsx`...  | `process.env`, `import.meta.env`, `Bun.env`, `Deno.env.get`, destructuring |
| Go       | `.go`                    | `os.Getenv`, `os.LookupEnv`, `os.Setenv`                     |
| Ruby     | `.rb`                    | `ENV[...]`, `ENV.fetch`                                      |

### Configuration sources (all gitignore-aware in reverse)

| Source          | Finds                                                   |
| --------------- | ------------------------------------------------------- |
| dotenv          | `.env`, `.env.local`, `.env.example`, ...               |
| docker-compose  | `services.*.environment` (list & map styles)            |
| github-actions  | `env:` maps in `.github/workflows/*`                    |
| kubernetes      | container `env`, `ConfigMap.data`, `Secret.data`        |
| terraform       | `variable ""`, `.tfvars`, `environment = {}` blocks     |

## Configuration

Config is optional. When you need it, use `conflint.toml` (or `pyproject.toml`
under `[tool.conflint]`):

```toml
[tool.conflint]
fail-level = "error"              # error | warning | info
require-example = true            # enforce a populated .env.example

enable = { CL003 = "error" }      # raise a rule's severity
disable = ["CL002"]               # turn rules off

ignore-names = ["CI=true", "NODE_ENV=*"]
ignore-paths = ["scripts/**", "vendor/**"]

sources = ["dotenv", "docker-compose", "github-actions", "kubernetes", "terraform"]
scanners = ["python", "javascript"]
reporters = ["text"]
```

Run `confl init` to write a commented template.

## CI integration

### GitHub Actions

```yaml
- name: Lint configuration
  uses: conflint/conflint@v1
  with:
    reporter: github          # inline PR annotations
    fail-level: error
```

or with pip directly:

```yaml
- uses: actions/setup-python@v5
  with: { python-version: "3.12" }
- run: pip install conflint
- run: confl check --github
```

### pre-commit

```yaml
- repo: https://github.com/conflint/conflint
  rev: v0.1.1
  hooks:
    - id: conflint
```

## Output formats

```bash
confl check                       # rich terminal output
confl check --json                # stable JSON schema (v1.0)
confl check --sarif               # SARIF 2.1.0 (CodeQL, Azure Pipelines, GitLab)
confl check --github              # GitHub Actions workflow commands
confl check --report junit        # JUnit XML for Jenkins dashboards
confl check --json --output report.json   # write to a file
```

## Development

```bash
git clone https://github.com/conflint/conflint
cd conflint
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

## License

MIT. See [LICENSE](LICENSE).

## Similar tools & why conflint is different

| Tool         | What it does                    | What conflint adds                     |
| ------------ | ------------------------------- | -------------------------------------- |
| `dotenv-linter` | validates `.env` against rules | reads your **code**, not a hand-made schema |
| `trufflehog`/`gitleaks` | scans git history for secrets | live per-key **value** + **drift** reconciliation in CI |
| envcheck-style CLIs | compare `.env.example` to `.env` | cross-source graph: code · .env · CI · k8s · terraform |
| `mypy`/`ruff` | static types/lint | the **configuration layer** they ignore |