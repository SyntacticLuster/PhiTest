# Security Policy

## Supported versions

ɸTest is currently pre-release (V1, untagged). Only the current `master` branch is supported. No backport patches are issued.

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

To report a vulnerability privately, use whichever of the following is available for this repository:

- GitHub private vulnerability reporting (Security tab → "Report a vulnerability"), if enabled
- A direct message to the maintainer via the repository's GitHub profile

If neither channel is available, open a GitHub issue with only enough detail to establish that a private disclosure is needed, and the maintainer will arrange a private channel.

## What to include in a report

- ɸTest version or commit SHA
- Python version and OS
- Description of the vulnerability and its potential impact
- Steps to reproduce
- Any relevant sanitized log output

**Do not include secrets, API tokens, or private subject/experiment data in your report.**

## Scope notes

- ɸTest is a local-first tool. It binds to localhost by default and is not designed for public internet exposure without additional hardening.
- The `HTTPJsonTarget` adapter sends HTTP requests to user-configured local endpoints. The URL scheme is validated (http/https only). Authentication tokens are read from environment variables and never stored in the database or audit log.
- Environment variable references (e.g., `PHITEST_TARGET_TOKEN`) are the expected mechanism for secrets. Do not commit `.env` files containing real tokens.
- The SQLite database contains experiment observations and audit events. Treat it as sensitive research data.

## Out of scope

- Vulnerabilities in the target system being tested (ɸTest is the testing framework, not the target)
- Issues requiring physical access to the machine running ɸTest
