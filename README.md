# flugmodus

## Setup

```sh
uv sync
uv run pre-commit install
```

## Pre-commit

Hooks are defined in `.pre-commit-config.yaml` and run automatically on commit and push:
basic file checks, `uv.lock` sync, Ruff linting/formatting and gitleaks secret scanning.
Direct commits to `main` are blocked.

- Run on all files: `uv run pre-commit run --all-files`
- Update hook versions: `uv run pre-commit autoupdate`

## Model erzeugen

```sh
uv run gen_model.py
```

## Keys erzeugen

```sh
uv run gen_keys.py
```

## Anwendung starten

```sh
uv run fastapi dev
```
