# API reference

The public surface of conflint is intentionally small: most projects only ever
interact with the `confl` CLI, and plugins subclass the three base classes.

::: conflint.config.Settings
    options:
      show_bases: false

::: conflint.models.Config

::: conflint.engine.Analyzer
    options:
      show_bases: false

::: conflint.scanners.base.Scanner

::: conflint.sources.base.ConfigSource

::: conflint.rules.base.Rule

::: conflint.reporters.base.Reporter