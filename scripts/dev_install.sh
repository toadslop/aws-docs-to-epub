#!/bin/bash
# Development installation script

set -e

echo "Installing aws-docs-to-epub in development mode..."

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Warning: Not in a virtual environment. Consider activating one first."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

echo "✓ Installation complete!"
echo ""
echo "You can now run:"
echo "  aws-docs-to-epub <url>"
echo ""
echo "Or as a module:"
echo "  python -m aws_docs_to_epub <url>"
echo ""
echo "Run tests with:"
echo "  pytest"
