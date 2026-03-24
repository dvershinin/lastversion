# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**lastversion** — CLI tool and Python library that finds the latest stable release version of software projects across multiple hosting platforms (GitHub, GitLab, PyPI, Bitbucket, SourceForge, WordPress, etc.). Used heavily in RPM build automation and CI/CD pipelines.

## Development Setup

- **Virtualenv:** `~/.virtualenvs/lastversion/`
- **Secrets:** Source `~/.secrets` before running tests (contains `GITHUB_API_TOKEN` and other API tokens)

## Common Commands

```bash
# Run all tests (sources secrets, activates venv, parallel execution with 10min timeout)
make test

# Run a single test
source ~/.secrets && ~/.virtualenvs/lastversion/bin/python -m pytest tests/test_github.py::test_function_name -v

# Lint
~/.virtualenvs/lastversion/bin/python -m flake8 src tests
~/.virtualenvs/lastversion/bin/python -m pylint src tests

# Security scan
~/.virtualenvs/lastversion/bin/python -m bandit -c pyproject.toml -r src/lastversion

# Release (CI auto-publishes to PyPI on GitHub release creation)
# 1. Bump __version__ in src/lastversion/__about__.py
# 2. Commit: git commit -m "chore(release): X.Y.Z"
# 3. Tag: git tag -s vX.Y.Z -m "vX.Y.Z"
# 4. Push: git push origin master && git push origin vX.Y.Z
# 5. Create release: gh release create vX.Y.Z --title "vX.Y.Z" --notes "..."
# CI workflow pythonpublish.yml handles PyPI upload automatically.
# Do NOT use `make publish` or manual `twine upload`.
make publish  # backup only, prefer CI

# Build single binary
make one-file
```

## Architecture

### Repository Holder Pattern

Core abstraction: `BaseProjectHolder` (in `src/lastversion/repo_holders/base.py`) is the abstract base class for all hosting platform adapters. Each adapter lives in `src/lastversion/repo_holders/` and implements release discovery for its platform.

`HolderFactory` (`holder_factory.py`) maintains an ordered registry of adapters and selects the appropriate one based on the input URL/name. Detection order matters — adapters are tried in registration order.

### Key Modules

- **`lastversion.py`** — Core logic: `latest()`, `has_update()`, `check_version()` entry points
- **`cli.py`** — CLI argument parsing, all subcommands (get, download, extract, install, update-spec, etc.)
- **`version.py`** — `Version` class extending `packaging.Version` with normalization for messy real-world version strings (dashed versions, Java-style, pre-release variants)
- **`cache.py`** — Dual-level caching: HTTP-level (CacheControl/ETag) + release-data-level (File or Redis backend) with PID-based file locking
- **`config.py`** — Platform-aware config singleton (`~/.config/lastversion/lastversion.yml` on Linux, `~/Library/Application Support/lastversion/lastversion.yml` on macOS)

### GitHub Adapter (`repo_holders/github.py`)

Most complex adapter. Uses GraphQL API with REST fallback. Handles rate limiting, API tokens (`GITHUB_API_TOKEN`/`GITHUB_TOKEN` env vars), commit-based version extraction, and release note parsing.

### RPM Spec Integration

`update-spec` command parses `.spec` files for `%{upstream_github}`, `%global lastversion_repo`, and `%global lastversion_*` directives to determine repo and version constraints.

## Testing

- **Framework:** pytest with pytest-xdist (parallel: `-n auto`)
- **CI matrix:** Python 3.6, 3.9, 3.13
- Tests include live API calls — require valid API tokens
- Test files mirror the module structure: `test_github.py`, `test_gitlab.py`, `test_pypi.py`, etc.
- Helper utilities in `tests/helpers.py`

## Linting

- **flake8:** max-line-length=120, select C,E,F,W,B,B950, ignore E203/E501/E704 (configured in `setup.cfg`)
- **bandit:** security scanning configured in `pyproject.toml`
- **pre-commit:** ruff, flake8, black, isort, bandit — all at line-length 120

## Code Style

- **Docstrings:** Google-style on all new/modified functions. First line: one-sentence imperative summary ending with a period. Include Args, Returns, Raises sections with type info even if type hints exist. Document coroutine behavior where relevant.
- **Interpreter:** Always use `~/.virtualenvs/lastversion/bin/python` — never bare `python` or `pytest`.
- **PRs:** Must include docstrings for new/modified functions. Must update `.cursor/rules/` if adding new modules or architectural changes.

## Python Compatibility

Supports Python 3.6+. Conditional dependencies exist for `cachecontrol` and `urllib3` based on Python version (see `setup.py`).
