#!/usr/bin/env python3
"""
AWS Documentation to EPUB converter
Fetches all pages from any AWS Developer Guide and converts them to EPUB format
"""

from urllib.parse import urljoin, urlsplit
import time
import os
import re
import json
import argparse
import sys

import requests
from bs4 import BeautifulSoup
from ebooklib import epub


class AWSDocsToEpub:
    """
    AWS Documentation to EPUB Converter.

    This class scrapes AWS documentation from docs.aws.amazon.com and converts it
    into an EPUB format for offline reading. It handles navigation parsing,
    content extraction, and EPUB generation with optional cover images.

    Attributes:
        start_url (str): The starting URL of the AWS documentation guide.
        base_url (str): The base URL for AWS documentation (https://docs.aws.amazon.com).
        cover_icon_url (str): Optional URL or file path for the cover icon image.
        service_name (str): The AWS service name extracted from the URL.
        version (str): The documentation version extracted from the URL.
        guide_type (str): The type of guide (e.g., 'user-guide', 'api-reference').
        guide_path (str): The full path to the guide on AWS documentation.
        session (requests.Session): HTTP session with configured headers for web scraping.
        pages (list): List of scraped page content.
        visited_urls (set): Set of URLs that have been processed to avoid duplicates.
        guide_title (str): The title of the documentation guide.
        guide_metadata (dict): Additional metadata about the guide.

    Example:
        >>> converter = AWSDocsToEpub(
        ...     'https://docs.aws.amazon.com/service/latest/userguide/index.html',
        ...     cover_icon_url='path/to/icon.svg'
        ... )
        >>> pages = converter.scrape_all_pages()
        >>> converter.create_epub(pages)
    """

    def __init__(self, start_url, cover_icon_url=None):
        self.start_url = start_url
        self.base_url = 'https://docs.aws.amazon.com'
        self.cover_icon_url = cover_icon_url

        # Parse the URL to extract guide information
        parsed_url = urlsplit(start_url)
        path_parts = [p for p in parsed_url.path.split('/') if p]

        # Extract service and guide type from URL
        # Typical format: /service/version/guide-type/page.html
        if len(path_parts) >= 3:
            self.service_name = path_parts[0]
            self.version = path_parts[1]
            self.guide_type = path_parts[2]
            self.guide_path = f"/{self.service_name}/{self.version}/{self.guide_type}/"
        else:
            raise ValueError(
                f"Unable to parse AWS documentation URL: {start_url}")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;q=0.9,'
                'image/webp,*/*;q=0.8'
            ),
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.pages = []
        self.visited_urls = set()
        self.guide_title = None
        self.guide_metadata = {}
        self.images = {}  # Cache for downloaded images: {url: (data, ext, media_type)}

    def fetch_page(self, url):
        """Fetch a page with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Fetching: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text
            except requests.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(
                        f"Failed to fetch {url} after {max_retries} attempts")
                    return None
        return None

    def download_image(self, img_url):
        """Download an image and return its data, extension, and media type"""
        # Check cache first
        if img_url in self.images:
            return self.images[img_url]

        try:
            # Detect format from URL
            url_lower = img_url.lower()
            if '.png' in url_lower:
                ext, media_type = 'png', 'image/png'
            elif '.jpg' in url_lower or '.jpeg' in url_lower:
                ext, media_type = 'jpg', 'image/jpeg'
            elif '.svg' in url_lower:
                ext, media_type = 'svg', 'image/svg+xml'
            elif '.gif' in url_lower:
                ext, media_type = 'gif', 'image/gif'
            elif '.webp' in url_lower:
                ext, media_type = 'webp', 'image/webp'
            else:
                # Default to PNG
                ext, media_type = 'png', 'image/png'

            response = self.session.get(img_url, timeout=30)
            response.raise_for_status()
            
            result = (response.content, ext, media_type)
            self.images[img_url] = result
            return result
        except requests.RequestException as e:
            print(f"Warning: Failed to download image {img_url}: {e}")
            return None, None, None

    def fetch_cover_icon(self):
        """Fetch the cover icon from URL or local file, return (data, extension, media_type)"""
        if not self.cover_icon_url:
            return None, None, None

        try:
            # Detect format from URL
            url_lower = self.cover_icon_url.lower()
            if '.png' in url_lower:
                ext, media_type = 'png', 'image/png'
            elif '.jpg' in url_lower or '.jpeg' in url_lower:
                ext, media_type = 'jpg', 'image/jpeg'
            elif '.svg' in url_lower:
                ext, media_type = 'svg', 'image/svg+xml'
            elif '.gif' in url_lower:
                ext, media_type = 'gif', 'image/gif'
            elif '.webp' in url_lower:
                ext, media_type = 'webp', 'image/webp'
            else:
                # Default to PNG if we can't determine
                ext, media_type = 'png', 'image/png'

            # Check if it's a local file
            if os.path.exists(self.cover_icon_url):
                with open(self.cover_icon_url, 'rb') as f:
                    return f.read(), ext, media_type
            # Otherwise treat as URL
            else:
                print(f"Fetching cover icon: {self.cover_icon_url}")
                response = self.session.get(self.cover_icon_url, timeout=30)
                response.raise_for_status()
                return response.content, ext, media_type
        except (OSError, requests.RequestException) as e:
            print(f"Warning: Failed to fetch cover icon: {e}")
            return None, None, None

    def extract_navigation(self, html_content):
        """Extract all page URLs from the navigation sidebar"""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []

        # Extract guide metadata if not already done
        if not self.guide_title:
            self.extract_guide_metadata(soup)

        # AWS docs use various structures, try multiple approaches
        # Look for all links in the entire page that match the guide URL pattern
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link['href']
            # Only include links that are part of this specific guide
            # and not external references or anchors only
            if self.guide_path in href and not href.endswith('.pdf'):
                full_url = urljoin(self.base_url, href)
                # Remove anchors
                full_url = full_url.split('#')[0]
                if full_url not in self.visited_urls:
                    title = link.get_text(strip=True) or 'Untitled'
                    # Skip empty titles or very short ones
                    if len(title) > 0:
                        links.append({
                            'url': full_url,
                            'title': title
                        })
                        self.visited_urls.add(full_url)

        return links

    def extract_guide_metadata(self, soup):
        """Extract guide title and metadata from the page"""
        # Try to get the guide title from meta tags or title
        title_tag = soup.find('meta', {'property': 'og:title'}) or soup.find(
            'meta', {'name': 'this_doc_guide'})
        if title_tag:
            self.guide_title = title_tag.get('content', 'AWS Documentation')
        else:
            title_elem = soup.find('title')
            if title_elem:
                self.guide_title = title_elem.get_text(
                    strip=True).split(' - ')[0]
            else:
                self.guide_title = 'AWS Documentation'

        # Extract product name
        product_tag = soup.find('meta', {'name': 'this_doc_product'})
        if product_tag:
            self.guide_metadata['product'] = product_tag.get('content', '')

    def parse_toc_json(self, toc_data, parent_title=''):
        """Recursively parse the TOC JSON and extract all pages"""
        pages = []

        if isinstance(toc_data, dict):
            title = toc_data.get('title', '')
            href = toc_data.get('href', '')

            if href and not href.endswith('.pdf'):
                full_url = urljoin(self.base_url + self.guide_path, href)
                if full_url not in self.visited_urls:
                    pages.append({
                        'url': full_url,
                        'title': title
                    })
                    self.visited_urls.add(full_url)

            # Recursively process nested contents
            if 'contents' in toc_data:
                for item in toc_data['contents']:
                    pages.extend(self.parse_toc_json(item, title))

        elif isinstance(toc_data, list):
            for item in toc_data:
                pages.extend(self.parse_toc_json(item, parent_title))

        return pages

    def fetch_toc_json(self):
        """Fetch the TOC JSON from the AWS documentation"""
        toc_url = urljoin(self.base_url + self.guide_path, 'toc-contents.json')
        try:
            print(f"Fetching TOC from: {toc_url}")
            response = self.session.get(toc_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
            print(f"Error fetching TOC JSON: {e}")
            return None

    def load_toc_from_json(self, json_file=None):
        """Load and parse the table of contents JSON file"""
        try:
            if json_file and os.path.exists(json_file):
                # Load from local file if provided and exists
                with open(json_file, 'r', encoding='utf-8') as f:
                    toc_data = json.load(f)
            else:
                # Fetch from AWS
                toc_data = self.fetch_toc_json()
                if not toc_data:
                    return []

            pages = self.parse_toc_json(toc_data)
            print(f"Loaded {len(pages)} pages from TOC")
            return pages
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error loading TOC: {e}")
            return []

    def extract_content(self, html_content, url):
        """Extract the main content from a page"""
        soup = BeautifulSoup(html_content, 'lxml')

        # Find the main content area
        # AWS docs typically use specific containers
        main_content = soup.find('main') or soup.find(
            'div', id='main-content') or soup.find('div', class_='documentation-content')

        if not main_content:
            # Fallback to body
            main_content = soup.find('body')

        if not main_content:
            return None

        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else 'Untitled'

        # Clean up the content
        # Remove navigation, scripts, noscript warnings, etc.
        for elem in main_content.find_all(
            ['script', 'style', 'nav', 'footer', 'header', 'noscript']
        ):
            elem.decompose()

        # Remove specific AWS documentation elements
        for elem in main_content.find_all('div', id='js_error_message'):
            elem.decompose()

        for elem in main_content.find_all('div', id='doc-conventions'):
            elem.decompose()

        # Remove page utilities, footer elements, and other AWS-specific tags
        for elem in main_content.find_all(
            ['awsdocs-page-utilities', 'awsdocs-copyright', 'awsdocs-thumb-feedback']
        ):
            elem.decompose()

        for elem in main_content.find_all('div', id='main-col-footer'):
            elem.decompose()

        for elem in main_content.find_all('div', class_='prev-next'):
            elem.decompose()

        # Convert relative links to absolute
        for link in main_content.find_all('a', href=True):
            link['href'] = urljoin(url, link['href'])

        # Track images but keep URLs as absolute for now
        # They will be replaced when creating the EPUB
        images_in_page = []
        for img in main_content.find_all('img', src=True):
            img_url = urljoin(url, img['src'])
            img['src'] = img_url
            images_in_page.append(img_url)

        return {
            'title': title,
            'content': str(main_content),
            'url': url,
            'images': images_in_page
        }

    def scrape_all_pages(self):
        """Scrape all pages from the guide"""
        # Try to load from TOC JSON first
        nav_links = self.load_toc_from_json()

        if not nav_links:
            # Fallback to scraping the HTML if TOC JSON fails
            print("Falling back to HTML scraping...")
            html = self.fetch_page(self.start_url)
            if not html:
                print("Failed to fetch the starting page")
                return []

            # Extract navigation links
            print("Extracting navigation links...")
            nav_links = self.extract_navigation(html)
            print(f"Found {len(nav_links)} links in navigation")

            # Also add the start page if not already in the list
            if self.start_url not in self.visited_urls:
                # Extract title from the start page
                soup = BeautifulSoup(html, 'html.parser')
                h1 = soup.find('h1')
                start_title = h1.get_text(strip=True) if h1 else 'Introduction'
                nav_links.insert(
                    0, {'url': self.start_url, 'title': start_title})
                self.visited_urls.add(self.start_url)

        # Fetch all pages
        all_pages = []
        for i, link in enumerate(nav_links, 1):
            print(f"Processing page {i}/{len(nav_links)}: {link['title']}")
            html = self.fetch_page(link['url'])
            if html:
                content = self.extract_content(html, link['url'])
                if content:
                    all_pages.append(content)
            time.sleep(0.5)  # Be respectful with rate limiting

        return all_pages

    def create_cover_page(self, service_name, image_filename):
        """Create an HTML cover page with centered icon and service name"""
        cover_html = f'''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Cover</title>
    <link rel="stylesheet" type="text/css" href="style/cover.css"/>
</head>
<body>
    <div class="cover-container">
        <img src="{image_filename}" alt="{service_name} Icon" class="cover-icon" />
        <h1 class="cover-title">{service_name}</h1>
    </div>
</body>
</html>'''
        return cover_html

    def create_epub(self, pages, output_filename=None):
        """Create an EPUB file from the scraped pages"""
        if not output_filename:
            # Generate filename from service name
            safe_name = re.sub(
                r'[^\w\s-]', '', self.service_name).strip().replace(' ', '_')
            output_filename = f'{safe_name}_{self.guide_type}.epub'

        book = epub.EpubBook()

        # Set metadata
        identifier = f'aws-{self.service_name}-{self.guide_type}'
        book.set_identifier(identifier)
        book.set_title(
            self.guide_title or f'AWS {self.service_name.upper()} {self.guide_type.title()}')
        book.set_language('en')
        book.add_author('Amazon Web Services')

        # Add cover image and page if provided
        cover_page = None
        if self.cover_icon_url:
            cover_image_data, img_ext, img_media_type = self.fetch_cover_icon()
            if cover_image_data:
                # Add the cover image to the book
                cover_image = epub.EpubItem(
                    uid="cover_icon",
                    file_name=f"cover_icon.{img_ext}",
                    media_type=img_media_type,
                    content=cover_image_data
                )
                book.add_item(cover_image)

                # Create CSS for cover page
                cover_css = epub.EpubItem(
                    uid="cover_style",
                    file_name="style/cover.css",
                    media_type="text/css",
                    content='''
                    body {
                        margin: 0;
                        padding: 0;
                        text-align: center;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        font-family: Arial, sans-serif;
                    }
                    .cover-container {
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        padding: 2em;
                    }
                    .cover-icon {
                        max-width: 300px;
                        max-height: 300px;
                        margin-bottom: 2em;
                    }
                    .cover-title {
                        font-size: 2.5em;
                        font-weight: bold;
                        color: #232F3E;
                        margin: 0;
                        text-align: center;
                    }
                    '''.strip()
                )
                book.add_item(cover_css)

                # Create cover page
                service_display_name = self.guide_title or f'AWS {self.service_name.upper()}'
                cover_html = self.create_cover_page(service_display_name, f"cover_icon.{img_ext}")
                cover_page = epub.EpubHtml(
                    title='Cover',
                    file_name='cover.xhtml',
                    lang='en'
                )
                cover_page.content = cover_html
                cover_page.add_item(cover_css)
                cover_page.add_item(cover_image)
                book.add_item(cover_page)

        # Download and add all images to the book
        print("Downloading and embedding images...")
        image_mapping = {}  # Maps original URL to local filename
        image_counter = 0
        
        for page in pages:
            for img_url in page.get('images', []):
                if img_url not in image_mapping:
                    img_data, img_ext, img_media_type = self.download_image(img_url)
                    if img_data:
                        image_counter += 1
                        local_filename = f"images/img_{image_counter:04d}.{img_ext}"
                        image_mapping[img_url] = local_filename
                        
                        # Add image to book
                        img_item = epub.EpubItem(
                            uid=f"image_{image_counter}",
                            file_name=local_filename,
                            media_type=img_media_type,
                            content=img_data
                        )
                        book.add_item(img_item)
        
        print(f"Embedded {len(image_mapping)} images")

        # Create chapters with local image references
        chapters = []
        for i, page in enumerate(pages, 1):
            chapter = epub.EpubHtml(
                title=page['title'],
                file_name=f'chap_{i:03d}.xhtml',
                lang='en'
            )
            # Check if content already has an h1 heading at the start
            content = page['content']
            soup = BeautifulSoup(content, 'lxml')
            first_h1 = soup.find('h1')

            # Replace external image URLs with local references
            for img in soup.find_all('img', src=True):
                if img['src'] in image_mapping:
                    img['src'] = image_mapping[img['src']]

            # If there's an h1 and it matches the title, use content as-is
            # Otherwise, add the h1 at the beginning
            if first_h1 and first_h1.get_text(strip=True) == page['title']:
                chapter.content = str(soup)
            else:
                chapter.content = f'<h1>{page["title"]}</h1>' + str(soup)
            book.add_item(chapter)
            chapters.append(chapter)

        # Create table of contents
        book.toc = tuple(chapters)

        # Add navigation files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Define spine
        if cover_page:
            book.spine = [cover_page, 'nav'] + chapters
        else:
            book.spine = ['nav'] + chapters

        # Write the EPUB file
        epub.write_epub(output_filename, book, {})
        print(f"\nEPUB created successfully: {output_filename}")
        return output_filename


def main():
    """Main entry point for the AWS Documentation to EPUB converter.
    Parses command-line arguments, validates the input URL, and orchestrates the conversion
    process from AWS documentation to EPUB format. The function handles error cases and
    provides progress feedback throughout the conversion.
    Raises:
        SystemExit: If URL validation fails, converter initialization fails, or no pages
                    were successfully scraped.
        $ python aws_docs_to_epub.py https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html
        $ python aws_docs_to_epub.py https://docs.aws.amazon.com/lambda/latest/dg/welcome.html -o lambda_guide.epub"""
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

    print(f"Guide: {converter.guide_title or 'Detecting...'}")
    print(f"Service: {converter.service_name}")
    print(f"Type: {converter.guide_type}\n")

    print("Step 1: Scraping all pages...")
    pages = converter.scrape_all_pages()
    print(f"Successfully scraped {len(pages)} pages\n")

    if pages:
        print("Step 2: Creating EPUB...")
        output_file = converter.create_epub(pages, args.output)
        print(f"\n✓ Done! EPUB file created: {output_file}")
        print(f"  Pages: {len(pages)}")
        print(f"  Title: {converter.guide_title}")
    else:
        print("\nNo pages were scraped. Please check the error messages above.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
