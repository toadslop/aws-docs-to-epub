#!/bin/bash
# Quick installation script for AWS Docs to EPUB Converter

echo "AWS Documentation to EPUB Converter - Setup"
echo "==========================================="
echo ""

# Check Python version
PYTHON_CMD=""
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python 3 not found. Please install Python 3.12 or higher."
    exit 1
fi

echo "✓ Found Python: $($PYTHON_CMD --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo ""
echo "Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install requests beautifulsoup4 ebooklib lxml

echo ""
echo "✓ Setup complete!"
echo ""
echo "Usage:"
echo "  python aws_docs_to_epub.py <AWS_DOCS_URL>"
echo ""
echo "Example:"
echo "  python aws_docs_to_epub.py https://docs.aws.amazon.com/lambda/latest/dg/welcome.html"
echo ""
