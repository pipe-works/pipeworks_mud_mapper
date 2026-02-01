# PipeWorks MUD Mapper

Procedural MUD world mapping and visualization tool for the pipe-works ecosystem.

## Overview

`pipeworks_mud_mapper` generates visual maps from MUD world data (JSON zone files). It's a standalone tool that can work with `pipeworks_mud_server` or any compatible world data format.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

*Coming soon*

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting
ruff check src/ tests/
black --check src/ tests/

# Format code
black src/ tests/
ruff check --fix src/ tests/
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE) for details.

## Related Projects

- [pipeworks_mud_server](https://github.com/pipe-works/pipeworks_mud_server) - The Undertaking MUD server
- [pipe-works](https://github.com/pipe-works/pipe-works) - Main project hub
