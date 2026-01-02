"""Main converter class that orchestrates AWS documentation to EPUB conversion."""

from urllib.parse import urlsplit
import re

from scraper import AWSScraper
from toc_parser import TOCParser
from epub_builder import EPUBBuilder


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
        scraper (AWSScraper): Scraper instance for fetching pages.
        toc_parser (TOCParser): TOC parser for extracting page list.
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

        # Initialize components
        self.scraper = AWSScraper()
        self.toc_parser = TOCParser(
            self.scraper.session, self.base_url, self.guide_path)

        self.guide_title = None
        self.guide_metadata = {}

    def scrape_all_pages(self, json_file=None, max_pages=None):
        """
        Scrape all pages from the AWS documentation guide.

        Args:
            json_file (str, optional): Path to a pre-downloaded TOC JSON file.
            max_pages (int, optional): Maximum number of pages to scrape (for testing).

        Returns:
            list: List of dictionaries containing scraped page data, where each dict has:
                - 'url': Page URL
                - 'title': Page title
                - 'content': HTML content
                - 'images': List of image URLs found on the page
        """
        # Load pages from TOC
        pages_info = self.toc_parser.load_toc(json_file)

        if not pages_info:
            print("Warning: No pages found in TOC")
            return []

        # Apply max_pages limit if specified
        if max_pages:
            pages_info = pages_info[:max_pages]
            print(f"Limited to {max_pages} pages for testing")

# Extract guide title from first page before scraping
        if pages_info and not self.guide_title:
            first_page_html = self.scraper.fetch_page(pages_info[0]['url'])
            if first_page_html:
                self.guide_title = self.scraper.extract_guide_title(
                    first_page_html)
                print(f"Guide title: {self.guide_title}")

        # Scrape pages
        pages = self.scraper.scrape_pages(pages_info)

        return pages

    def create_epub(self, pages, output_filename=None):
        """
        Create an EPUB file from scraped pages.

        Args:
            pages (list): List of page dictionaries from scrape_all_pages()
            output_filename (str, optional): Custom output filename. If None, generates
                                            from service name and guide type.

        Returns:
            str: Path to the created EPUB file
        """
        if not pages:
            print("Error: No pages to create EPUB")
            return None

        # Generate filename from service name if not provided
        if not output_filename:
            safe_name = re.sub(
                r'[^\w\s-]', '', self.service_name).strip().replace(' ', '_')
            output_filename = f'{safe_name}_{self.guide_type}.epub'

        # Create EPUB book
        book_title = self.guide_title or f'AWS {self.service_name.upper()} {self.guide_type.title()}'
        identifier = f'aws-{self.service_name}-{self.guide_type}'

        builder = EPUBBuilder(
            title=book_title,
            author='Amazon Web Services',
            identifier=identifier
        )

        # Add cover image if provided
        if self.cover_icon_url:
            print("Generating cover image...")
            builder.add_cover(self.cover_icon_url)

        # Add CSS
        builder.add_css()

        # Download and add images
        print("Downloading and embedding images...")
        image_mapping = self._download_images(pages, builder)
        print(f"Embedded {len(image_mapping)} images")

        # Create chapters
        print("Creating chapters...")
        for page in pages:
            self._add_chapter_with_images(builder, page, image_mapping)

        # Finalize and write
        builder.finalize()
        builder.write(output_filename)

        print(f"\nEPUB created successfully: {output_filename}")
        print(f"  Pages: {len(pages)}")
        print(f"  Title: {book_title}")

        return output_filename

    def _download_images(self, pages, builder):
        """Download all images referenced in pages and add to EPUB."""
        from image_utils import fetch_image_from_url
        from ebooklib import epub

        image_mapping = {}
        image_counter = 0

        for page in pages:
            for img_url in page.get('images', []):
                if img_url not in image_mapping:
                    img_data, img_ext, img_media_type = fetch_image_from_url(
                        img_url)
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
                        builder.book.add_item(img_item)

        return image_mapping

    def _add_chapter_with_images(self, builder, page, image_mapping):
        """Add a chapter to the book with local image references."""
        from bs4 import BeautifulSoup

        content = page['content']
        soup = BeautifulSoup(content, 'html.parser')

        # Replace external image URLs with local references
        for img in soup.find_all('img', src=True):
            if img['src'] in image_mapping:
                img['src'] = image_mapping[img['src']]

        # Check if content already has an h1 heading at the start
        first_h1 = soup.find('h1')

        # If there's an h1 matching the title, use content as-is
        # Otherwise, add the h1 at the beginning
        if first_h1 and first_h1.get_text(strip=True) == page['title']:
            final_content = str(soup)
        else:
            final_content = f'<h1>{page["title"]}</h1>' + str(soup)

        builder.add_chapter(page['title'], final_content, page['url'])
