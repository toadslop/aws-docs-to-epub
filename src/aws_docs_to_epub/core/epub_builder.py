"""EPUB book creation and management."""

import os
import re
import traceback
from typing import Union, List, Optional, Dict, Any, Tuple

from ebooklib import epub
from bs4 import BeautifulSoup
import requests

from .image_utils import fetch_image_from_url, fetch_local_image, render_cover_image


class EPUBBuilder:
    """Handles EPUB book creation and content management."""

    def __init__(
            self,
            title: str,
            author: str = 'AWS Documentation',
            language: str = 'en',
            identifier: Optional[str] = None) -> None:
        self.book: epub.EpubBook = epub.EpubBook()
        self.title: str = title
        self.author: str = author

        # Set metadata
        self.book.set_title(title)
        self.book.set_language(language)
        self.book.add_author(author)

        if identifier:
            self.book.set_identifier(identifier)

        self.chapters: List[epub.EpubHtml] = []
        self.toc_items: List[epub.EpubHtml] = []
        self.spine: List[Union[str, epub.EpubHtml]] = ['nav']
        self.css: Optional[epub.EpubItem] = None
        self.url_to_filename: Dict[str, str] = {}

    def add_cover(self, cover_icon_url: str) -> None:
        """Generate and add cover image to the book."""

        try:
            # Fetch the icon
            if os.path.isfile(cover_icon_url):
                print(f"Loading cover icon from file: {cover_icon_url}")
                icon_data, icon_ext = fetch_local_image(cover_icon_url)
            else:
                print(f"Fetching cover icon from URL: {cover_icon_url}")
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                    'Accept': 'image/*,*/*;q=0.8'
                })
                icon_data, icon_ext = fetch_image_from_url(
                    cover_icon_url, session)

            if not icon_data:
                print("Failed to fetch cover icon")
                return

            # Render the cover
            cover_img = render_cover_image(self.title, icon_data, icon_ext)
            if cover_img:
                self.book.set_cover('cover.png', cover_img)
                print("Cover image added successfully")
            else:
                print("Failed to render cover image")
        except (requests.RequestException, OSError, ValueError) as e:
            print(f"Error adding cover: {e}")

            traceback.print_exc()

    def add_css(self) -> epub.EpubItem:
        """Add default CSS stylesheet to the book."""
        css_content = '''
@namespace epub "http://www.idpf.org/2007/ops";

body {
    font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
    margin: 5%;
    padding: 0;
    font-size: 1em;
    line-height: 1.5;
}

h1 {
    font-size: 1.6em;
    font-weight: bold;
    text-align: left;
    color: #000;
    margin: 1.2em 0 0.6em 0;
    line-height: 1.3;
}

h2 {
    font-size: 1.4em;
    font-weight: bold;
    text-align: left;
    color: #000;
    margin: 1em 0 0.5em 0;
    line-height: 1.3;
}

h3 {
    font-size: 1.2em;
    font-weight: bold;
    text-align: left;
    color: #000;
    margin: 1em 0 0.5em 0;
    line-height: 1.3;
}

h4 {
    font-size: 1.1em;
    font-weight: bold;
    text-align: left;
    color: #222;
    margin: 0.9em 0 0.4em 0;
    line-height: 1.3;
}

h5 {
    font-size: 1em;
    font-weight: bold;
    text-align: left;
    color: #333;
    margin: 0.8em 0 0.4em 0;
    line-height: 1.3;
}

h6 {
    font-size: 0.95em;
    font-weight: bold;
    text-align: left;
    color: #444;
    margin: 0.8em 0 0.4em 0;
    line-height: 1.3;
}

p {
    text-align: justify;
    margin: 0.5em 0;
}

pre, code {
    font-family: Monaco, Courier New, monospace;
    background-color: #f4f4f4;
    border: 1px solid #ddd;
    padding: 0.5em;
    overflow-x: auto;
}

p code {
    display: inline;
    font-family: Monaco, Courier New, monospace;
    background-color: #f9f9f9;
    border: 1px solid #e0e0e0;
    padding: 0.1em 0.3em;
    border-radius: 3px;
    font-size: 0.9em;
}

pre.programlisting {
    font-family: Monaco, Courier New, monospace;
    background-color: #f8f8f8;
    border-left: 3px solid #0066cc;
    padding: 0.6em 0.6em 0.6em 0.9em;
    margin: 1em 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
    line-height: 1.5;
    overflow-x: visible;
    font-size: 0.9em;
}

pre.programlisting code {
    background-color: transparent;
    border: none;
    padding: 0;
    display: block;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
    /* Create hanging indent for wrapped lines */
    text-indent: -1.2em;
    padding-left: 1.2em;
}

img {
    max-width: 100%;
    height: auto;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
}

th {
    background-color: #f4f4f4;
}

a {
    color: #0066cc;
    text-decoration: none;
}
'''
        nav_css = epub.EpubItem(
            uid="style_main",
            file_name="style/styles.css",
            media_type="text/css",
            content=css_content
        )
        self.book.add_item(nav_css)
        self.css = nav_css
        return nav_css

    def sanitize_filename(self, title: str) -> str:
        """Convert title to a valid filename."""
        filename = re.sub(r'[^\w\s-]', '', title)
        filename = re.sub(r'[-\s]+', '_', filename)
        return filename[:50].lower()

    def add_chapter(
            self, title: str, content: str, source_url: Optional[str] = None
    ) -> epub.EpubHtml:
        """Add a chapter to the book."""
        filename = self.sanitize_filename(title)
        xhtml_filename = f'{filename}.xhtml'

        # Create chapter
        chapter = epub.EpubHtml(
            title=title,
            file_name=xhtml_filename,
            lang='en'
        )

        # Track URL to filename mapping if source URL provided
        if source_url:
            self.url_to_filename[source_url] = xhtml_filename

        # Clean and set content
        chapter.content = self._clean_content(content)

        # Link CSS stylesheet if available
        if self.css:
            chapter.add_item(self.css)

        # Add to book
        self.book.add_item(chapter)
        self.chapters.append(chapter)
        self.toc_items.append(chapter)
        self.spine.append(chapter)

        return chapter

    def _clean_content(self, html_content: str) -> str:
        """Clean HTML content for EPUB compatibility."""
        if not html_content:
            return '<p>Content not available</p>'

        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove scripts and styles
        for element in soup.find_all(['script', 'style']):
            element.decompose()

        # Fix image paths
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src and isinstance(src, str):
                if src.startswith('//'):
                    img['src'] = 'https:' + src
                elif src.startswith('/'):
                    img['src'] = 'https://docs.aws.amazon.com' + src

        # Wrap in div if no body tag
        if not soup.find('body'):
            content = f'<div>{str(soup)}</div>'
        else:
            content = str(soup.body) if soup.body else str(soup)

        return content

    def _build_nested_toc(
            self,
            toc_structure: List[Dict[str, Any]],
            chapter_map: Dict[str, epub.EpubHtml]
    ) -> Tuple[Union[epub.EpubHtml, Tuple[Any, ...]], ...]:
        """Convert hierarchical TOC structure to ebooklib tuple format."""
        result: List[Union[epub.EpubHtml, Tuple[Any, ...]]] = []

        for item in toc_structure:
            url = item.get('url')
            children = item.get('children', [])

            if url and url in chapter_map:
                chapter = chapter_map[url]

                if children:
                    # Has children - create nested tuple (parent, (children))
                    child_toc = self._build_nested_toc(children, chapter_map)
                    result.append((chapter, child_toc))
                else:
                    # Leaf node - just add chapter
                    result.append(chapter)
            elif children:
                # No URL but has children - process children directly
                result.extend(self._build_nested_toc(children, chapter_map))

        return tuple(result)

    def finalize(self, toc_structure: Optional[List[Dict[str, Any]]] = None,
                 chapter_map: Optional[Dict[str, epub.EpubHtml]] = None) -> None:
        """Finalize the book structure with optional nested TOC."""
        # Add table of contents
        if toc_structure and chapter_map:
            # Build nested TOC structure
            self.book.toc = list(self._build_nested_toc(
                toc_structure, chapter_map))
        else:
            # Fallback to flat TOC
            self.book.toc = self.toc_items

        # Add navigation files
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        # Set spine
        self.book.spine = self.spine

    def write(self, output_path: str) -> None:
        """Write the EPUB file."""
        epub.write_epub(output_path, self.book)
        print(f"EPUB saved to: {output_path}")

    def get_chapter_count(self) -> int:
        """Return the number of chapters in the book."""
        return len(self.chapters)
