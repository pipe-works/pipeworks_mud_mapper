#!/bin/bash
# Install git hooks for pipeworks_mud_mapper
#
# This script installs custom git hooks from scripts/hooks/ into .git/hooks/
# Run this after cloning the repository.
#
# Usage:
#   ./scripts/install-hooks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_SOURCE="$SCRIPT_DIR/hooks"
HOOKS_DEST="$REPO_ROOT/.git/hooks"

echo "Installing git hooks..."

# Check we're in a git repo
if [ ! -d "$HOOKS_DEST" ]; then
    echo "Error: .git/hooks directory not found. Are you in a git repository?"
    exit 1
fi

# Install prepare-commit-msg hook
if [ -f "$HOOKS_SOURCE/prepare-commit-msg" ]; then
    cp "$HOOKS_SOURCE/prepare-commit-msg" "$HOOKS_DEST/prepare-commit-msg"
    chmod +x "$HOOKS_DEST/prepare-commit-msg"
    echo "  - Installed prepare-commit-msg hook"
fi

echo ""
echo "Git hooks installed successfully!"
echo ""
echo "The prepare-commit-msg hook will automatically generate commit messages"
echo "for data-only changes (data/maps/, data/validation/) with [skip ci]."
