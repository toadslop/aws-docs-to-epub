# AWS Documentation to EPUB Converter

A universal command-line tool that converts any AWS Developer Guide to EPUB format for offline reading.

## Features

- 🚀 Works with **any** AWS Developer Guide (Lambda, EKS, S3, MSK, etc.)
- 📚 Automatically discovers and downloads all pages in the guide
- 🎯 Preserves the original table of contents structure
- 📖 Creates properly formatted EPUB files compatible with all readers
- ⚡ Smart rate limiting to be respectful to AWS servers
- 🔄 Automatic fallback if TOC is unavailable

## Requirements

- Python 3.12+
- requests
- beautifulsoup4
- ebooklib
- lxml

All dependencies are installed in the `.venv` virtual environment.

## Installation

```bash
# Clone or download this repository
cd convert2

# Activate the virtual environment (already configured)
source .venv/bin/activate
```

## Usage

### Basic Usage

Convert any AWS Developer Guide by providing its URL:

```bash
python aws_docs_to_epub.py <URL>
```

### Examples

**AWS MSK Developer Guide:**
```bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html
# Creates: msk_developerguide.epub
```

**AWS Lambda Developer Guide:**
```bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
# Creates: lambda_dg.epub
```

**AWS EKS User Guide:**
```bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
# Creates: eks_userguide.epub
```

**With Custom Output Filename:**
```bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/s3/latest/userguide/Welcome.html -o my_s3_guide.epub
```

### Command-Line Options

```
usage: aws_docs_to_epub.py [-h] [-o OUTPUT] [--version] url

positional arguments:
  url                   URL to any page in the AWS Developer Guide

options:
  -h, --help            Show help message and exit
  -o OUTPUT, --output OUTPUT
                        Custom output EPUB filename
  --version             Show version number
```

## How It Works

1. **Parse URL**: Extracts the service name, version, and guide type from the URL
2. **Fetch TOC**: Downloads `toc-contents.json` from the guide's documentation
3. **Extract Pages**: Recursively parses the TOC to find all page URLs
4. **Download Content**: Fetches each page with proper error handling and rate limiting
5. **Clean Content**: Removes navigation, scripts, and other non-content elements
6. **Build EPUB**: Compiles everything into a standards-compliant EPUB file

## Output

The script creates EPUB files with:
- ✅ Proper metadata (title, author, identifier)
- ✅ Complete table of contents
- ✅ All content from the guide
- ✅ Preserved formatting and structure
- ✅ Compatible with Apple Books, Calibre, Adobe Digital Editions, and other readers

## Performance

- **Rate Limiting**: 0.5 second delay between page requests
- **Typical Guides**: 
  - Small guides (~100 pages): 1-2 minutes
  - Medium guides (~300 pages): 2-3 minutes  
  - Large guides (~500 pages): 4-5 minutes

## Supported Guides

Works with any AWS documentation that follows the standard structure:
- `https://docs.aws.amazon.com/<service>/<version>/<guide-type>/<page>.html`

Examples:
- Developer Guides (`/latest/developerguide/`)
- User Guides (`/latest/userguide/`)
- API References (`/latest/APIReference/`)
- Administration Guides (`/latest/adminguide/`)

## Files

- `aws_docs_to_epub.py` - Main conversion script
- `README.md` - This file
- `*.epub` - Generated EPUB files

## Troubleshooting

**Error: "Unable to parse AWS documentation URL"**
- Ensure the URL is a valid AWS documentation URL starting with `https://docs.aws.amazon.com/`

**Error: "Failed to fetch TOC"**
- Check your internet connection
- The guide may not have a standard TOC file (script will fall back to HTML parsing)

**No pages scraped**
- The guide structure may be non-standard
- Check the console output for specific error messages

## License

This tool is for personal use. AWS documentation is © Amazon Web Services, Inc. or its affiliates.

## Examples of Successfully Converted Guides

- ✅ AWS MSK Developer Guide (295 pages)
- ✅ AWS Lambda Developer Guide (443 pages)
- ✅ AWS EKS User Guide
- ✅ AWS S3 User Guide
- ✅ And many more!
