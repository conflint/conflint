# Rules

Rules run over the *config model* — the union of everything scanned from code
(usages) and everything parsed from configuration sources (entries). Each rule
has a default severity that `--fail-level` and the `enable`/`disable` settings
can tune.

## CL001 — missing (`error`)

A configuration value is read by code but defined in **no** configuration
source. The runtime profile will crash on this key.

**Fix:** add the key to `.env` (or wherever it should live), then `confl sync`
to refresh `.env.example`.

## CL002 — unused (`warning`)

A real configuration value (from `.env`, CI, k8s, terraform, ...) is never read
by any scanned code. It may be dead config, or the scanner may not understand
your access pattern.

## CL003 — typo (`warning`)

An undefined value closely matches a defined one (edit distance ≤ 2). High signal
for `DBHOST` vs `DB_HOST` type bugs.

## CL004 — secret-leak (`error`)

A high-entropy secret value (Shannon entropy above the configured threshold,
default 3.5) is committed in a **real** (non-example) configuration source.
Example files are exempt.

## CL005 — drift (`error`)

A value is documented in an example file (`.env.example` etc.) but provided by
no real source. The promised interface is stale.

## CL006 — empty-value (`warning`)

A value required by code is defined but left empty. It will arrive at runtime
as an empty string.

## CL007 — duplicate (`warning`)

A key is defined more than once, or real sources disagree on its value. The last
definition wins — often not the one you intended.

## CL008 — weak-secret (`warning`)

A secret-looking value (sensitive name) equals a weak or default placeholder
like `changeme`, `your-api-key`, `secret`, or a 1-char value.

## CL009 — undocumented (`info`)

A value is used by code or provided by a real source but missing from any
example file. Fires only when `require-example` is `true` (the default) and an
example file already exists.

## Tunable behaviours

| Setting | Affects |
| --- | --- |
| `entropy-threshold` | CL004 sensitivity |
| `ignore-names` | names exempt from all rules |
| `ignore-paths` | paths exempt from scanning |
| `enable` / `disable` | per-rule severity or off switch |
| `require-example` | CL005 / CL009 enablement |