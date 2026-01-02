"""Web scraping utilities for AWS documentation."""

from urllib.parse import urljoin
import time
import requests
from bs4 import BeautifulSoup


class AWSScraper:
    """Handles scraping AWS documentation pages."""

    def __init__(self):
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
        self.visited_urls = set()

    def fetch_page(self, url):
        """Fetch a page with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Fetching: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(
                        f"Failed to fetch {url} after {max_retries} attempts")
                    return None
        return None

    def extract_content(self, html_content, url):
        """Extract the main content from a page."""
        soup = BeautifulSoup(html_content, 'lxml')

        # Find the main content area
        main_content = soup.find('main') or soup.find('div', id='main-content') or \
            soup.find('div', class_='documentation-content')

        if not main_content:
            main_content = soup.find('body')

        if not main_content:
            return None

        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else 'Untitled'

        # Clean up the content - remove navigation, scripts, etc.
        for elem in main_content.find_all(['script', 'style', 'nav', 'footer', 'header', 'noscript']):
            elem.decompose()

        # Remove specific AWS documentation elements
        for elem in main_content.find_all('div', id=['js_error_message', 'doc-conventions', 'main-col-footer']):
            elem.decompose()

        for elem in main_content.find_all(['awsdocs-page-utilities', 'awsdocs-copyright', 'awsdocs-thumb-feedback']):
            elem.decompose()

        for elem in main_content.find_all('div', class_=['prev-next', 'code-btn-container', 'btn-copy-code']):
            elem.decompose()

        for elem in main_content.find_all('awsui-icon'):
            elem.decompose()

        # Remove id attributes and invalid custom attributes
        invalid_attrs = ['tab-id', 'data-target', 'data-toggle', 'copy']
        for elem in main_content.find_all(True):
            if elem.has_attr('id'):
                del elem['id']
            for attr in invalid_attrs:
                if elem.has_attr(attr):
                    del elem[attr]

        # Convert relative links to absolute
        for link in main_content.find_all('a', href=True):
            link['href'] = urljoin(url, link['href'])

        # Track images
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

    def scrape_pages(self, page_links, max_pages=None):
        """Scrape content from a list of page links."""
        if max_pages and max_pages > 0:
            page_links = page_links[:max_pages]
            print(f"Limiting to first {max_pages} pages for testing")

        all_pages = []
        for i, link in enumerate(page_links, 1):
            print(f"Processing page {i}/{len(page_links)}: {link['title']}")
            html = self.fetch_page(link['url'])
            if html:
                content = self.extract_content(html, link['url'])
                if content:
                    all_pages.append(content)
            time.sleep(0.5)  # Rate limiting

        return all_pages

    def extract_guide_title(self, html):
        """Extract the guide title from a page's meta tags."""
        soup = BeautifulSoup(html, 'html.parser')

        # Try to get from meta tags (product + guide)
        product_meta = soup.find('meta', {'name': 'product'})
        guide_meta = soup.find('meta', {'name': 'guide'})

        if product_meta and guide_meta:
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
