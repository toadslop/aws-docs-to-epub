# AWS Documentation to EPUB Converter

Convert AWS Developer Guide documentation to EPUB format for offline reading.

## Features

- 📚 Converts any AWS Developer Guide to EPUB format
- 🎨 Generates beautiful cover images with service icons
- 🖼️ Downloads and embeds all images
- 📑 Preserves table of contents structure
- 🔧 Supports SVG, PNG, JPG, and other image formats
- ⚡ Efficient scraping with rate limiting
- 🎯 Test mode with page limits

## Installation

### From Source

```bash
git clone <repository-url>
cd convert2
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Basic Usage

```bash
aws-docs-to-epub https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html
```

### With Custom Output Filename

```bash
aws-docs-to-epub URL -o my-guide.epub
```

### With Cover Icon

```bash
aws-docs-to-epub URL -c icon.svg
```

### Test Mode (Limited Pages)

```bash
aws-docs-to-epub URL --max-pages 5
```

## Project Structure

```
convert2/
├── src/aws_docs_to_epub/    # Main package
│   ├── cli.py                # CLI interface
│   ├── converter.py          # Main converter orchestration
│   └── core/                 # Core functionality modules
├── tests/                    # Test suite
└── scripts/                  # Development scripts
```

## Requirements

- Python 3.8+
- requests
- beautifulsoup4
- ebooklib
- Pillow (PIL)
- cairosvg (for SVG support)

## License

MIT License
