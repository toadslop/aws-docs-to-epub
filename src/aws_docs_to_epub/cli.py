#!/usr/bin/env python3
"""Command-line interface for AWS Documentation to EPUB converter."""

import argparse
import sys

from .converter import AWSDocsToEpub


def main() -> None:
    # pylint: disable=line-too-long
    """Main entry point for the AWS Documentation to EPUB converter.

    Parses command-line arguments, validates the input URL, and orchestrates the conversion
    process from AWS documentation to EPUB format. The function handles error cases and
    provides progress feedback throughout the conversion.

    Raises:
        SystemExit: If URL validation fails, converter initialization fails, or no pages
                    were successfully scraped.

    Examples:
        $ aws-docs-to-epub https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html
        $ aws-docs-to-epub https://docs.aws.amazon.com/lambda/latest/dg/welcome.html -o lambda_guide.epub
    """
    parser = argparse.ArgumentParser(
        description='Convert AWS Developer Guide documentation to EPUB format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert AWS MSK Developer Guide
  %(prog)s https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html
  
  # Convert AWS Lambda Developer Guide
  %(prog)s https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
  
  # Convert with custom output filename
  %(prog)s https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html -o eks_guide.epub
  
  # Convert with custom cover icon
  %(prog)s https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html -c icon.svg
        """
    )
    parser.add_argument(
        'url',
        help='URL to any page in the AWS Developer Guide'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output EPUB filename (default: auto-generated from guide name)',
        default=None
    )
    parser.add_argument(
        '-c', '--cover-icon',
        help='URL or filepath to cover icon image (PNG, JPG, SVG, GIF, WebP)',
        default=None,
        dest='cover_icon'
    )
    parser.add_argument(
        '--custom-css',
        help='Path to custom CSS file to override default styles',
        default=None,
        dest='custom_css'
    )
    parser.add_argument(
        '--max-pages',
        help='Maximum number of pages to scrape (for testing)',
        type=int,
        default=None,
        dest='max_pages'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='AWS Docs to EPUB Converter 1.0'
    )

    args = parser.parse_args()

    # Validate URL
    if not args.url.startswith('https://docs.aws.amazon.com/'):
        print("Error: URL must be an AWS documentation URL (docs.aws.amazon.com)", file=sys.stderr)
        sys.exit(1)

    print("AWS Documentation to EPUB Converter")
    print("=" * 50)
    print(f"Source URL: {args.url}\n")

    try:
        converter = AWSDocsToEpub(args.url, args.cover_icon)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Service: {converter.config.service_name}")
    print(f"Type: {converter.config.guide_type}\n")

    print("Step 1: Scraping all pages...")
    pages = converter.scrape_all_pages(max_pages=args.max_pages)

    if not pages:
        print("\nNo pages were scraped. Please check the error messages above.", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully scraped {len(pages)} pages\n")

    print("Step 2: Creating EPUB...")
    output_file = converter.create_epub(pages, args.output, args.custom_css)

    if output_file:
        print(f"\n✓ Done! EPUB file created: {output_file}")
        print(f"  Pages: {len(pages)}")
        print(f"  Title: {converter.metadata.title or 'N/A'}")
    else:
        print("\nFailed to create EPUB. Please check the error messages above.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
