"""Table of Contents parsing for AWS documentation."""

from urllib.parse import urljoin
import json
import os
from typing import Optional, Dict, Any, List, Set, Union
import requests


class TOCParser:
    """Handles parsing of AWS documentation table of contents."""

    def __init__(self, session: requests.Session, base_url: str, guide_path: str) -> None:
        self.session: requests.Session = session
        self.base_url: str = base_url
        self.guide_path: str = guide_path
        self.visited_urls: Set[str] = set()

    def fetch_toc_json(self) -> Optional[Any]:
        """Fetch the TOC JSON from the AWS documentation."""
        toc_url = urljoin(self.base_url + self.guide_path, 'toc-contents.json')
        try:
            print(f"Fetching TOC from: {toc_url}")
            response = self.session.get(toc_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            print(f"Error fetching TOC JSON: {e}")
            return None

    def parse_toc_json(
            self, toc_data: Union[Dict[str, Any], List[Any]], parent_title: str = ''
    ) -> List[Dict[str, Any]]:
        """Recursively parse the TOC JSON and extract all pages with hierarchy."""
        pages: List[Dict[str, Any]] = []

        if isinstance(toc_data, dict):
            title = toc_data.get('title', '')
            href = toc_data.get('href', '')

            # Create page entry with children support
            page_entry: Dict[str, Any] = {
                'title': title,
                'url': None,
                'children': []
            }

            if href and not href.endswith('.pdf'):
                full_url = urljoin(self.base_url + self.guide_path, href)
                if full_url not in self.visited_urls:
                    page_entry['url'] = full_url
                    self.visited_urls.add(full_url)

            # Recursively process nested contents
            if 'contents' in toc_data:
                for item in toc_data['contents']:
                    child_pages = self.parse_toc_json(item, title)
                    page_entry['children'].extend(child_pages)

            # Only add entries that have a URL or children
            if page_entry['url'] or page_entry['children']:
                pages.append(page_entry)

        elif isinstance(toc_data, list):
            for item in toc_data:
                pages.extend(self.parse_toc_json(item, parent_title))

        return pages

    def load_toc(self, json_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load and parse the table of contents JSON file."""
        try:
            if json_file and os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    toc_data = json.load(f)
            else:
                toc_data = self.fetch_toc_json()
                if not toc_data:
                    return []

            pages = self.parse_toc_json(toc_data)

            # Count total pages (including nested)
            def count_pages(page_list: List[Dict[str, Any]]) -> int:
                count = 0
                for page in page_list:
                    if page.get('url'):
                        count += 1
                    count += count_pages(page.get('children', []))
                return count

            total = count_pages(pages)
            print(f"Loaded {total} pages from TOC (with hierarchy)")
            return pages
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error loading TOC: {e}")
            return []
