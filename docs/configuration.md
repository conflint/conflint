# Configuration

Configuration is optional. When you need it, put a **flat** `conflint.toml` in
the project root (or a `.conflint.toml`), or nest the same keys under
`[tool.conflint]` in `pyproject.toml`.

Run `confl init` to write a commented template.

```toml
# conflint.toml — keys are top-level here.
# In pyproject.toml they are nested under [tool.conflint].

fail-level = "error"              # error | warning | info
require-example = true            # enforce a populated .env.example

enable = { CL003 = "error" }      # raise a rule's severity
disable = ["CL002", "CL009"]      # turn rules off

ignore-names = ["CI=true", "NODE_ENV=*"]
ignore-paths = ["scripts/**", "vendor/**"]

include = ["**/*"]                # code globs (relative to the project root)
exclude = [".git/**", "**/node_modules/**", ...]

sources = ["dotenv", "docker-compose", "github-actions", "kubernetes", "terraform"]
scanners = ["python", "javascript"]
reporters = ["text"]              # default reporter(s) for `confl check`

color = true                      # ANSI in text output
entropy-threshold = 3.5           # CL004 secret sensitivity

example-files = [".env.example", ".env.sample", ...]
```

Config file resolution order (later wins):

1. `pyproject.toml` → `[tool.conflint]`
2. `conflint.toml`, then `.conflint.toml`
3. `--config FILE` on the command line
4. CLI flags (`--fail-level`, `--no-color`, positional paths)

Unknown keys raise a configuration error so typos surface immediately.

## Reference

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `include` | list of globs | `["**/*"]` | code files to scan |
| `exclude` | list of globs | system defaults | paths to skip |
| `scanners` | list of names | all | enabled language scanners |
| `sources` | list of names | all | enabled config sources |
| `enable` | table rule→severity | — | override a rule's severity |
| `disable` | list of rule ids | — | turn rules off |
| `ignore-names` | list of globs | — | exempt names from all rules |
| `ignore-paths` | list of globs | — | exempt paths from scanning |
| `fail-level` | `error`/`warning`/`info` | `error` | exit threshold for `check` |
| `example-files` | list of names | system defaults | example/template files |
| `color` | bool | auto | ANSI in text output |
| `entropy-threshold` | float | `3.5` | CL004 sensitivity |
| `require-example` | bool | `true` | require a populated example file |
| `reporters` | list of names | `["text"]` | default output for `check` |

`CLI overrides` for paths and `--fail-level`/`--no-color` always win because
they come last.