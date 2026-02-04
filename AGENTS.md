# Repository Guidelines

## Project Structure & Module Organization
- `src/pipeworks_mud_mapper/` holds the Dash app, models, services, callbacks, and UI components. Entry point: `app.py`.
- `tests/` contains pytest suites (naming: `test_*.py`).
- `data/maps/` stores authoring files (`*.map.json` with coordinates).
- `data/zones/` stores exported game files (`*.json` without coordinates).
- Policy: commit/push `data/maps/` and `data/zones/` when they change; ignore `data/maps/dev_snapshots/`.
- `docs/` contains Sphinx documentation sources.

## Build, Test, and Development Commands
- `pip install -e ".[dev]"` installs dev dependencies.
- `pre-commit install` enables required hooks (run once after cloning).
- `python -m pipeworks_mud_mapper` starts the local Dash app.
- `pytest` runs tests with coverage reports.
- `ruff check src/ tests/` runs linting.
- `black src/ tests/` formats code.
- `mypy src/ --ignore-missing-imports` runs type checks.
- `pre-commit run --all-files` runs the full hook suite.

## Coding Style & Naming Conventions
- Python 3.12+ only.
- Formatting: Black (line length 100). Linting: Ruff with E/F/I/N/W/UP rules.
- Type checks: Mypy (lenient but required).
- Tests allow `MockClass` naming and unused variables in `tests/**` via Ruff per-file ignores.

## Testing Guidelines
- Framework: pytest with `pytest-cov`.
- Naming: files `test_*.py`, functions `test_*`.
- Coverage: CI enforces `--cov-fail-under=25` (org target is 50% per `CLAUDE.md`).
- Markers: `unit`, `integration`, `slow` (skip slow with `-m "not slow"`).

## Commit & Pull Request Guidelines
- Use Conventional Commits seen in history (e.g., `feat(ui): ...`, `fix(validation): ...`, `chore(data): ...`).
- Prefer feature branches and PRs; avoid direct pushes to `main`.
- PRs should include a clear summary and note UI changes with screenshots or a short GIF when applicable.
- Update docs when behavior or user flows change.

## Agent-Specific Notes
- Run `pre-commit install` after cloning and `pre-commit run --all-files` before pushing.
- Keep mapper behavior deterministic when randomness is involved.
