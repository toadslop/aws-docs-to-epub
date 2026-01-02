# Refactored Code Structure

The AWS Docs to EPUB converter has been refactored from a single 840-line file into a modular structure for better maintainability and testability.

## File Structure

```
convert2/
├── aws_docs_to_epub.py      # Main entry point (CLI interface)
├── converter.py              # Core converter orchestration
├── scraper.py                # Web scraping functionality
├── toc_parser.py             # Table of contents parsing
├── epub_builder.py           # EPUB book creation
├── image_utils.py            # Image handling and cover generation
├── aws_docs_to_epub_old.py  # Backup of original monolithic file
└── .venv/                    # Python virtual environment
```

## Module Descriptions

### aws_docs_to_epub.py
**Purpose**: Main entry point for the CLI application
- Argument parsing (URL, output file, cover icon, max pages)
- Input validation
- Error handling
- Progress feedback

### converter.py
**Purpose**: Orchestrates the conversion process
- `AWSDocsToEpub` class - main converter class
- URL parsing to extract service/guide information
- Coordinates scraping, TOC parsing, and EPUB building
- Manages image downloading and embedding
- Creates chapters with localized image references

### scraper.py
**Purpose**: Web scraping functionality
- `AWSScraper` class for fetching AWS documentation pages
- HTTP session management with proper headers
- Retry logic with exponential backoff
- Content extraction and cleaning
- HTML sanitization (removes navigation, scripts, AWS UI elements)
- Image URL extraction and normalization

### toc_parser.py
**Purpose**: Table of contents parsing
- `TOCParser` class for handling AWS TOC JSON files
- Fetches toc-contents.json from AWS documentation
- Recursively parses nested TOC structure
- Extracts all page URLs and titles
- Deduplicates URLs to avoid processing same page twice

### epub_builder.py
**Purpose**: EPUB book creation and management
- `EPUBBuilder` class for building EPUB files
- Metadata management (title, author, identifier)
- Cover image generation and embedding
- CSS stylesheet creation
- Chapter creation with proper XHTML formatting
- Navigation and table of contents generation
- Final EPUB file writing

### image_utils.py
**Purpose**: Image handling and cover generation
- Image fetching from URLs (handles gzip-compressed SVGs)
- Local file image loading
- SVG to PNG conversion using cairosvg
- Cover image rendering with icon + text
- Support for multiple image formats (PNG, JPG, SVG, GIF, WebP)

## Key Improvements

### Separation of Concerns
- Each module has a single, well-defined responsibility
- Easier to locate and modify specific functionality
- Better code organization and readability

### Testability
- Modules can be tested independently
- Mock dependencies easily in unit tests
- Smaller, focused functions are easier to test

### Maintainability
- Changes to scraping logic don't affect EPUB building
- Cover generation logic is isolated
- TOC parsing can be modified without touching core conversion

### Reusability
- Image utilities can be used in other projects
- Scraper can be adapted for different documentation sites
- EPUB builder can create books from any content source

## Usage

The CLI interface remains unchanged:

```bash
# Basic usage
python aws_docs_to_epub.py https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html

# With custom output and cover
python aws_docs_to_epub.py URL -o output.epub -c cover.svg

# Test with limited pages
python aws_docs_to_epub.py URL --max-pages 5
```

## Dependencies

The refactored code maintains all original dependencies:
- requests - HTTP requests
- beautifulsoup4 - HTML parsing
- ebooklib - EPUB creation
- Pillow (PIL) - Image manipulation
- cairosvg - SVG to PNG conversion

## Testing

Test the refactored code:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run with test parameters
python aws_docs_to_epub.py 'https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html' --max-pages 3 -o test.epub

# Validate EPUB (requires epubcheck)
epubcheck test.epub
```

## Migration Notes

- Original monolithic file backed up as `aws_docs_to_epub_old.py`
- All functionality preserved in refactored modules
- CLI interface unchanged - scripts using the tool will continue to work
- Virtual environment (.venv) remains unchanged
