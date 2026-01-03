# Internal Link Rewriting Implementation

## Overview

This implementation adds automatic internal link rewriting to the EPUB conversion process. When AWS documentation pages link to other pages within the same guide, those links are now converted to point directly to the corresponding chapters within the EPUB file, rather than to external web URLs.

## How It Works

### 1. URL Tracking
- The `EPUBBuilder` class now maintains a `url_to_filename` dictionary that maps original documentation URLs to chapter filenames in the EPUB
- When a chapter is added via `add_chapter()`, the source URL is recorded if provided

### 2. Link Detection
The `_rewrite_internal_links()` method in the `AWSDocsToEpub` converter:
- Parses all hyperlinks in each chapter
- Identifies internal links by checking if they:
  - Point to `docs.aws.amazon.com`
  - Use the same guide path as the current documentation
- Checks if the target URL exists in the URL-to-filename mapping

### 3. Link Rewriting
For identified internal links:
- The external URL is replaced with the relative EPUB chapter filename
- Fragment identifiers (e.g., `#section-name`) are preserved if present
- External links and links to other AWS services are left unchanged

### 4. ID Attribute Preservation
- Modified the scraper to preserve `id` attributes on HTML elements
- This ensures fragment links (`page.html#section`) work correctly
- Only truly invalid attributes (`tab-id`, `data-target`, etc.) are removed

## Example

**Before (in scraped HTML):**
```html
<p>See the <a href="https://docs.aws.amazon.com/msk/latest/developerguide/getting-started.html">Getting Started</a> guide.</p>
<p>Visit <a href="https://docs.aws.amazon.com/msk/latest/developerguide/api-ref.html#create-cluster">Create Cluster API</a>.</p>
```

**After (in EPUB):**
```html
<p>See the <a href="getting_started.xhtml">Getting Started</a> guide.</p>
<p>Visit <a href="api_ref.xhtml#create-cluster">Create Cluster API</a>.</p>
```

## Benefits

1. **Offline Navigation**: Readers can click links within the EPUB to navigate between sections without requiring internet access
2. **Better Reading Experience**: Links work natively in EPUB readers
3. **Maintains References**: All cross-references between documentation pages are preserved
4. **Smart Detection**: Only converts links within the same guide; external links remain unchanged

## Files Modified

- `src/aws_docs_to_epub/core/epub_builder.py`: Added URL tracking
- `src/aws_docs_to_epub/core/scraper.py`: Preserved ID attributes  
- `src/aws_docs_to_epub/converter.py`: Implemented link rewriting logic
- `tests/unit/test_internal_links.py`: Added comprehensive tests
- `tests/unit/test_scraper.py`: Updated tests for ID preservation
- `tests/unit/test_converter_extended.py`: Updated mocking for new method

## Testing

All 144 tests pass, including:
- Unit tests for URL mapping
- Unit tests for internal vs external link detection
- Unit tests for fragment preservation
- Integration tests with epubcheck validation
