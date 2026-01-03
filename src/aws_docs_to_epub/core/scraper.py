"""Web scraping utilities for AWS documentation."""

from urllib.parse import urljoin
import time
from typing import Optional, Dict, Any, List, Set
import requests
from bs4 import BeautifulSoup, Tag


class AWSScraper:
    """Handles scraping AWS documentation pages."""

    def __init__(self) -> None:
        self.session: requests.Session = requests.Session()
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
        self.visited_urls: Set[str] = set()

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Fetching: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text
            except (requests.RequestException, ConnectionError, TimeoutError) as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(
                        f"Failed to fetch {url} after {max_retries} attempts")
                    return None
        return None

    def extract_content(self, html_content: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract the main content from a page."""
        soup = BeautifulSoup(html_content, 'lxml')

        main_content = self._find_main_content(soup)
        if not main_content:
            return None

        title = self._extract_title(soup)
        self._clean_content(main_content)
        self._fix_links_and_images(main_content, url)

        images_in_page = [urljoin(url, str(img['src']))
                          for img in main_content.find_all('img', src=True)]

        return {
            'title': title,
            'content': str(main_content),
            'url': url,
            'images': images_in_page
        }

    def _find_main_content(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the main content area of the page."""
        main_content = soup.find('main') or soup.find('div', id='main-content') or \
            soup.find('div', class_='documentation-content')
        return main_content or soup.find('body')  # type: ignore[return-value]

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title."""
        title_elem = soup.find('h1') or soup.find('title')
        return title_elem.get_text(strip=True) if title_elem else 'Untitled'

    def _clean_content(self, main_content: Tag) -> None:
        """Remove unwanted elements from the content."""
        # Remove navigation, scripts, etc.
        for elem in main_content.find_all(
            ['script', 'style', 'nav', 'footer', 'header', 'noscript']
        ):
            elem.decompose()

        # Remove specific AWS documentation elements
        for elem in main_content.find_all(
            'div', id=['js_error_message', 'doc-conventions', 'main-col-footer']
        ):
            elem.decompose()

        for elem in main_content.find_all(
                ['awsdocs-page-utilities', 'awsdocs-copyright',
                    'awsdocs-thumb-feedback']
        ):
            elem.decompose()

        for elem in main_content.find_all(
            'div', class_=['prev-next', 'code-btn-container', 'btn-copy-code']
        ):
            elem.decompose()

        for elem in main_content.find_all('awsui-icon'):
            elem.decompose()

        # Remove invalid attributes
        self._remove_invalid_attributes(main_content)

    def _remove_invalid_attributes(self, main_content: Tag) -> None:
        """Remove invalid attributes from elements."""
        invalid_attrs = ['tab-id', 'data-target', 'data-toggle', 'copy']
        for elem in main_content.find_all(True):
            # Keep id attributes as they're needed for fragment links
            # Only remove specifically invalid attributes
            for attr in invalid_attrs:
                if elem.has_attr(attr):
                    del elem[attr]

    def _fix_links_and_images(self, main_content: Tag, url: str) -> None:
        """Convert relative URLs to absolute URLs."""
        for link in main_content.find_all('a', href=True):
            href = link.get('href', '')
            if isinstance(href, str):
                link['href'] = urljoin(url, href)

        for img in main_content.find_all('img', src=True):
            src = img.get('src', '')
            if isinstance(src, str):
                img['src'] = urljoin(url, src)

    def scrape_pages(self,
                     page_links: List[Dict[str, str]],
                     max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape content from a list of page links."""
        if max_pages and max_pages > 0:
            page_links = page_links[:max_pages]
            print(f"Limiting to first {max_pages} pages for testing")

        all_pages: List[Dict[str, Any]] = []
        for i, link in enumerate(page_links, 1):
            print(f"Processing page {i}/{len(page_links)}: {link['title']}")
            html = self.fetch_page(link['url'])
            if html:
                content = self.extract_content(html, link['url'])
                if content:
                    all_pages.append(content)
            time.sleep(0.5)  # Rate limiting

        return all_pages

    def extract_guide_title(self, html: str) -> str:
        """Extract the guide title from a page's meta tags."""
        soup = BeautifulSoup(html, 'html.parser')

        # Try to get from meta tags (product + guide)
        product_meta = soup.find('meta', {'name': 'product'})
        guide_meta = soup.find('meta', {'name': 'guide'})

        if (product_meta and guide_meta and
                hasattr(product_meta, 'get') and hasattr(guide_meta, 'get')):
            product = product_meta.get('content', '')
            guide = guide_meta.get('content', '')
            if product and guide:
                return f"{product} {guide}"

        # Fallback to title tag
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            # Remove page-specific part (everything before " - ")
            if ' - ' in title_text:
                return title_text.split(' - ', 1)[1]
            return title_text

        return "AWS Documentation"
