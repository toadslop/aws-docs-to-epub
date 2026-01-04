"""Main converter class that orchestrates AWS documentation to EPUB conversion."""

from urllib.parse import urlsplit, urlparse
import re
from dataclasses import dataclass
from typing import Optional, Any, Dict, List

from ebooklib import epub
from bs4 import BeautifulSoup

from .core.scraper import AWSScraper
from .core.toc_parser import TOCParser
from .core.epub_builder import EPUBBuilder
from .core.image_utils import fetch_image_from_url


@dataclass
class GuideConfig:
    """Configuration extracted from AWS documentation URL."""
    service_name: str
    version: str
    guide_type: str
    guide_path: str
    start_url: str
    base_url: str = 'https://docs.aws.amazon.com'


@dataclass
class GuideMetadata:
    """Metadata about the documentation guide."""
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


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

    def __init__(self, start_url: str, cover_icon_url: Optional[str] = None) -> None:
        self.cover_icon_url: Optional[str] = cover_icon_url

        # Parse the URL to extract guide information
        parsed_url = urlsplit(start_url)
        path_parts = [p for p in parsed_url.path.split('/') if p]

        # Extract service and guide type from URL
        # Typical format: /service/version/guide-type/page.html
        if len(path_parts) >= 3:
            service_name = path_parts[0]
            version = path_parts[1]
            guide_type = path_parts[2]
            guide_path = f"/{service_name}/{version}/{guide_type}/"

            self.config: GuideConfig = GuideConfig(
                service_name=service_name,
                version=version,
                guide_type=guide_type,
                guide_path=guide_path,
                start_url=start_url
            )
        else:
            raise ValueError(
                f"Unable to parse AWS documentation URL: {start_url}")

        # Initialize components
        self.scraper: AWSScraper = AWSScraper()
        self.toc_parser: TOCParser = TOCParser(
            self.scraper.session, self.config.base_url, self.config.guide_path)

        self.metadata: GuideMetadata = GuideMetadata()
        self.toc_structure: List[Dict[str, Any]] = []

    def _flatten_toc(self, toc_structure: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Flatten hierarchical TOC structure to simple list of pages."""
        flat_pages: List[Dict[str, str]] = []

        for item in toc_structure:
            url = item.get('url')
            if url:
                flat_pages.append({
                    'url': url,
                    'title': item['title']
                })
            # Recursively process children
            children = item.get('children', [])
            if children:
                flat_pages.extend(self._flatten_toc(children))

        return flat_pages

    def scrape_all_pages(
        self,
        json_file: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
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
        # Load hierarchical TOC structure
        self.toc_structure = self.toc_parser.load_toc(json_file)

        if not self.toc_structure:
            print("Warning: No pages found in TOC")
            return []

        # Flatten to get list of URLs for scraping
        pages_info = self._flatten_toc(self.toc_structure)

        # Apply max_pages limit if specified
        if max_pages:
            pages_info = pages_info[:max_pages]
            print(f"Limited to {max_pages} pages for testing")

# Extract guide title from first page before scraping
        if pages_info and not self.metadata.title:
            first_page_html = self.scraper.fetch_page(pages_info[0]['url'])
            if first_page_html:
                self.metadata.title = self.scraper.extract_guide_title(
                    first_page_html)
                print(f"Guide title: {self.metadata.title}")

        # Scrape pages
        pages: List[Dict[str, Any]] = self.scraper.scrape_pages(pages_info)

        return pages

    def create_epub(
        self,
        pages: List[Dict[str, Any]],
        output_filename: Optional[str] = None,
        custom_css_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Create an EPUB file from scraped pages.

        Args:
            pages (list): List of page dictionaries from scrape_all_pages()
            output_filename (str, optional): Custom output filename. If None, generates
                                            from service name and guide type.
            custom_css_path (str, optional): Path to custom CSS file to override default styles.

        Returns:
            str: Path to the created EPUB file
        """
        if not pages:
            print("Error: No pages to create EPUB")
            return None

        # Generate filename from service name if not provided
        if not output_filename:
            safe_name = re.sub(
                r'[^\w\s-]', '', self.config.service_name).strip().replace(' ', '_')
            output_filename = f'{safe_name}_{self.config.guide_type}.epub'

        # Create EPUB book
        book_title = (
            self.metadata.title
            or f'AWS {self.config.service_name.upper()} {self.config.guide_type.title()}'
        )
        identifier = f'aws-{self.config.service_name}-{self.config.guide_type}'

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
        builder.add_css(custom_css_path)

        # Download and add images
        print("Downloading and embedding images...")
        image_mapping = self._download_images(pages, builder)
        print(f"Embedded {len(image_mapping)} images")

        # First pass: create chapters and build URL mapping
        print("Creating chapters...")
        chapter_map: Dict[str, epub.EpubHtml] = {}
        for page in pages:
            chapter = self._add_chapter_with_images(
                builder, page, image_mapping)
            if chapter:
                chapter_map[page['url']] = chapter

        # Second pass: rewrite internal links
        print("Rewriting internal links...")
        self._rewrite_internal_links(builder)

        # Finalize with nested TOC structure
        builder.finalize(toc_structure=self.toc_structure,
                         chapter_map=chapter_map)
        builder.write(output_filename)

        print(f"\nEPUB created successfully: {output_filename}")
        print(f"  Pages: {len(pages)}")
        print(f"  Title: {book_title}")

        return output_filename

    def _download_images(
        self,
        pages: List[Dict[str, Any]],
        builder: EPUBBuilder
    ) -> Dict[str, str]:
        """Download all images referenced in pages and add to EPUB."""

        image_mapping = {}
        image_counter = 0

        for page in pages:
            for img_url in page.get('images', []):
                if img_url not in image_mapping:
                    img_data, img_ext = fetch_image_from_url(
                        img_url, self.scraper.session)
                    if img_data:
                        image_counter += 1
                        local_filename = f"images/img_{image_counter:04d}.{img_ext}"
                        image_mapping[img_url] = local_filename

                        # Determine media type from extension
                        media_types: Dict[str, str] = {
                            'jpg': 'image/jpeg',
                            'jpeg': 'image/jpeg',
                            'png': 'image/png',
                            'gif': 'image/gif',
                            'svg': 'image/svg+xml',
                            'webp': 'image/webp'
                        }
                        img_media_type = media_types.get(
                            img_ext.lower(), 'image/jpeg')

                        # Add image to book
                        img_item = epub.EpubItem(
                            uid=f"image_{image_counter}",
                            file_name=local_filename,
                            media_type=img_media_type,
                            content=img_data
                        )
                        builder.book.add_item(img_item)

        return image_mapping

    def _add_chapter_with_images(
        self,
        builder: EPUBBuilder,
        page: Dict[str, Any],
        image_mapping: Dict[str, str]
    ) -> Optional[epub.EpubHtml]:
        """Add a chapter to the book with local image references."""

        content = page['content']
        soup = BeautifulSoup(content, 'html.parser')

        # Replace external image URLs with local references
        for img in soup.find_all('img', src=True):
            img_src = str(img['src'])
            if img_src in image_mapping:
                img['src'] = image_mapping[img_src]

        # Check if content already has an h1 heading at the start
        first_h1 = soup.find('h1')

        # If there's an h1 matching the title, use content as-is
        # Otherwise, add the h1 at the beginning
        if first_h1 and first_h1.get_text(strip=True) == page['title']:
            final_content = str(soup)
        else:
            final_content = f'<h1>{page["title"]}</h1>' + str(soup)

        return builder.add_chapter(page['title'], final_content, page['url'])

    def _rewrite_internal_links(
        self,
        builder: EPUBBuilder
    ) -> None:
        """Rewrite internal links to point to chapters in the EPUB."""
        base_url = self.config.base_url
        guide_path = self.config.guide_path

        for chapter in builder.chapters:
            soup = BeautifulSoup(chapter.content, 'html.parser')
            links_rewritten = 0

            for link in soup.find_all('a', href=True):
                href = str(link['href'])

                # Parse the link to determine if it's internal
                parsed_href = urlparse(href)

                # Check if this is an internal link
                # Internal links are those that:
                # 1. Point to the same base domain and guide path
                # 2. Are in our set of scraped pages
                is_internal = False
                target_url = href

                # If it's an absolute URL
                if parsed_href.netloc:
                    # Check if it's pointing to docs.aws.amazon.com with our guide path
                    if (parsed_href.netloc == 'docs.aws.amazon.com' and
                            parsed_href.path.startswith(guide_path)):
                        is_internal = True
                        # Normalize the URL (remove fragment for lookup)
                        target_url = f"{base_url}{parsed_href.path}"
                        if parsed_href.query:
                            target_url += f"?{parsed_href.query}"

                if is_internal and target_url in builder.url_to_filename:
                    # Rewrite to internal EPUB link
                    target_filename = builder.url_to_filename[target_url]

                    # Preserve fragment if present (for in-page anchors)
                    if parsed_href.fragment:
                        link['href'] = f"{target_filename}#{parsed_href.fragment}"
                    else:
                        link['href'] = target_filename

                    links_rewritten += 1

            if links_rewritten > 0:
                # Update chapter content with rewritten links
                chapter.content = str(soup)
                print(
                    f"  Rewrote {links_rewritten} internal link(s) in: {chapter.title}")
