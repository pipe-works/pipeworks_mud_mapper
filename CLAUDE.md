# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PipeWorks MUD Mapper** is a procedural MUD world mapping and visualization tool. It generates visual maps from MUD world data (JSON zone files) and is designed as a standalone tool in the pipe-works ecosystem.

**Tech Stack**: Python 3.12+

**Status**: Initial setup - architecture and features to be defined.

## Common Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (REQUIRED after cloning)
pre-commit install

# Run tests
pytest

# Run linting
ruff check src/ tests/
black --check src/ tests/

# Format code
black src/ tests/
ruff check --fix src/ tests/

# Type checking
mypy src/ --ignore-missing-imports

# Run all pre-commit checks manually
pre-commit run --all-files
```

## Architecture

```
src/pipeworks_mud_mapper/
├── __init__.py          # Package init, version
└── (modules TBD)        # Mapper implementation
```

## Development Guidelines

- Follow pipe-works organization coding standards
- **Always run `pre-commit install` after cloning** - hooks are not automatic
- All code must pass pre-commit hooks before committing (ruff, black, mypy, bandit)
- Run `pre-commit run --all-files` to check before pushing if hooks weren't triggered
- Write tests for new functionality (50% minimum coverage)
- Use feature branches and PRs - avoid pushing directly to main
- Update documentation as needed
- Determinism is important where applicable (seeded RNG)

## Integration Points

- **Input**: JSON world data (compatible with `pipeworks_mud_server` zone format)
- **Output**: Visual maps (format TBD - ASCII, SVG, image)

## pipe-works Organization Standards

This repository follows pipe-works organization standards.
See https://github.com/pipe-works/pipe-works/blob/main/CLAUDE.md for full details.

- Python 3.12+, pyenv virtualenvs
- pytest with >50% coverage (org minimum)
- black 26.1.0 (pinned org-wide) / ruff / mypy
- Reusable CI workflow from pipe-works/.github
- GPL-3.0-or-later license

## License

This project is licensed under GPL-3.0-or-later.
