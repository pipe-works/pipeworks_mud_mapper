"""Basic tests to verify package setup."""

import re

import pipeworks_mud_mapper


def test_version():
    """Package has a valid semver version string."""
    version = pipeworks_mud_mapper.__version__
    assert version is not None
    assert re.match(r"^\d+\.\d+\.\d+", version), f"Invalid version format: {version}"
