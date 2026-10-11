# Plugins

conflint is small by design. Language support, configuration sources and rules
are all pluggable through Python entry points, so you only install the parts
you need — and anyone can contribute the ones you don't.

## Entry point groups

| Group | Provides | Objects returned |
| --- | --- | --- |
| `conflint.scanners` | language scanners | `Scanner` subclasses |
| `conflint.sources` | config-file parsers | `ConfigSource` subclasses |
| `conflint.rules` | rules | `Rule` subclasses |

Built-ins are registered in `pyproject.toml`:

```toml
[project.entry-points."conflint.scanners"]
python = "conflint.scanners.python:PythonScanner"
javascript = "conflint.scanners.javascript:JavaScriptScanner"
go = "conflint.scanners.go:GoScanner"
ruby = "conflint.scanners.ruby:RubyScanner"

[project.entry-points."conflint.sources"]
dotenv = "conflint.sources.dotenv:DotenvSource"
docker_compose = "conflint.sources.docker_compose:DockerComposeSource"
github_actions = "conflint.sources.github_actions:GitHubActionsSource"
kubernetes = "conflint.sources.kubernetes:KubernetesSource"
terraform = "conflint.sources.terraform:TerraformSource"

[project.entry-points."conflint.rules"]
CL001 = "conflint.rules.missing:MissingRule"
# ... CL002–CL009
```

## Writing a scanner

A `Scanner` declares the file extensions it handles and turns `(path, text)`
into `Usage` objects. Scanners never touch the filesystem — the engine reads
the file and hands over the contents:

```python
from conflint.models import Usage
from conflint.scanners.base import Scanner

class RustScanner(Scanner):
    name = "rust"
    extensions = (".rs",)

    def scan(self, path, text: str) -> list[Usage]:
        # find `std::env::var("FOO")` and friends, return Usage(...)
        ...
```

Register it with the `conflint.scanners` entry point, reinstall your package,
and `confl check` discovers it automatically.

## Writing a source

A `ConfigSource` declares the glob patterns it owns (these intentionally
**bypass `.gitignore`** — a `.env` is usually gitignored on purpose) and parses
files into `Entry` objects:

```python
from conflint.models import Entry
from conflint.sources.base import ConfigSource

class NomadSource(ConfigSource):
    name = "nomad"
    config_globs = ("*.nomad", "nomad/*.hcl")

    def parse(self, path, text: str) -> list[Entry]:
        ...
```

Sources must **never raise on malformed input** — skip what you cannot parse.

## Writing a rule

```python
from conflint.config import Settings
from conflint.models import Config, Finding, Severity
from conflint.rules.base import Rule

class MyRule(Rule):
    id = "CL010"
    name = "my-rule"
    severity = Severity.WARNING
    description = "..."

    def check(self, config: Config, settings: Settings) -> list[Finding]:
        ...
```

Pick the next free `CLxxx` id for new rules so the namespace stays unique.

## Rules of the road

- **No filesystem access in rules.** Rules receive the already-built
  `Config` model; everything they need is on it.
- **Sources own line numbers.** Return `Entry`/`Usage` with accurate
  `Location`s — reporters, sync and `explain` all rely on them.
- Name your entry points by what they **are** (`python`, `dotenv`) so settings
  like `scanners = ["python"]` stay intuitive.