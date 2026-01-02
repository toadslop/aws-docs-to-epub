"""EPUB book creation and management."""

from ebooklib import epub
from bs4 import BeautifulSoup
from image_utils import render_cover_image
import re


class EPUBBuilder:
    """Handles EPUB book creation and content management."""

    def __init__(self, title, author='AWS Documentation', language='en', identifier=None):
        self.book = epub.EpubBook()
        self.title = title
        self.author = author

        # Set metadata
        self.book.set_title(title)
        self.book.set_language(language)
        self.book.add_author(author)

        if identifier:
            self.book.set_identifier(identifier)

        self.chapters = []
        self.toc_items = []
        self.spine = ['nav']

    def add_cover(self, cover_icon_url):
        """Generate and add cover image to the book."""
        import os
        import requests
        from image_utils import fetch_image_from_url, fetch_local_image, render_cover_image

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
        except Exception as e:
            print(f"Error adding cover: {e}")
            import traceback
            traceback.print_exc()

    def add_css(self):
        """Add default CSS stylesheet to the book."""
        css_content = '''
@namespace epub "http://www.idpf.org/2007/ops";

body {
    font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
    margin: 5%;
    padding: 0;
}

h1, h2, h3, h4, h5, h6 {
    text-align: left;
    color: #000;
    margin: 1em 0 0.5em 0;
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
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=css_content
        )
        self.book.add_item(nav_css)
        return nav_css

    def sanitize_filename(self, title):
        """Convert title to a valid filename."""
        filename = re.sub(r'[^\w\s-]', '', title)
        filename = re.sub(r'[-\s]+', '_', filename)
        return filename[:50].lower()

    def add_chapter(self, title, content, page_url):
        """Add a chapter to the book."""
        filename = self.sanitize_filename(title)

        # Create chapter
        chapter = epub.EpubHtml(
            title=title,
            file_name=f'{filename}.xhtml',
            lang='en'
        )

        # Clean and set content
        chapter.content = self._clean_content(content)

        # Add to book
        self.book.add_item(chapter)
        self.chapters.append(chapter)
        self.toc_items.append(chapter)
        self.spine.append(chapter)

        return chapter

    def _clean_content(self, html_content):
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

    def finalize(self):
        """Finalize the book structure."""
        # Add table of contents
        self.book.toc = self.toc_items

        # Add navigation files
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        # Set spine
        self.book.spine = self.spine

    def write(self, output_path):
        """Write the EPUB file."""
        epub.write_epub(output_path, self.book)
        print(f"EPUB saved to: {output_path}")

    def get_chapter_count(self):
        """Return the number of chapters in the book."""
        return len(self.chapters)
