# Security Policy

## Reporting a vulnerability

conflint is a developer tool; the most important security consideration is that
it **reads your configuration and source files** and reports what it finds. Do
not run `confl` output through shell `eval`, and treat the `sync` output as
example/template data only.

If you discover a security issue:

1. Do **not** open a public issue.
2. Email the maintainers at `security@conflint.dev` (or open a private advisory
   via GitHub's "Report a vulnerability" flow on the repository).
3. Include a minimal reproducer, affected versions, and your proposed fix if
   you have one.

We aim to acknowledge within 5 business days and to ship a fix for supported
minor versions.

## Supported versions

| Version | Supported          |
| --- |---------------------|
| latest release | Yes |
| previous minor | Best-effort |

## What we consider a vulnerability

- Remote code execution, arbitrary file read/write, or secret disclosure
  triggered by running `confl` on attacker-controlled input.
- Secret values being written to logs or non-maskable output.
- Malicious packaging / dependency confusion attacks on `conflint` itself.

## Things that are NOT vulnerabilities

- A rule reporting a value that the user chose to check (secret rendering in
  the SARIF/JSON/text output of a deliberately-run audit is the tool's purpose;
  use `--ignore-names` or disable rules to skip specific values).