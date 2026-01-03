"""Tests for improved code coverage."""

import unittest
from unittest.mock import patch
import sys
import subprocess
from PIL import Image, ImageDraw
from bs4 import BeautifulSoup
import requests

from aws_docs_to_epub.converter import AWSDocsToEpub
from aws_docs_to_epub.core.epub_builder import EPUBBuilder
from aws_docs_to_epub.core.scraper import AWSScraper
from aws_docs_to_epub.core.image_utils import (
    _paste_icon,
    _split_text_into_lines,
    _load_font,
    _calculate_optimal_font_and_text
)
from aws_docs_to_epub.commands import __all__


class TestCoverageImprovements(unittest.TestCase):
    """Tests to improve code coverage."""

    def test_scraper_fetch_page_returns_none_on_timeout(self):
        """Test that fetch_page returns None after all retries exhausted."""
        scraper = AWSScraper()

        # Mock session.get to always raise TimeoutError
        with patch.object(scraper.session, 'get', side_effect=TimeoutError("Timeout")):
            with patch('time.sleep'):  # Don't actually sleep
                result = scraper.fetch_page("https://example.com")

        self.assertIsNone(result)

    def test_scraper_fetch_page_returns_none_on_connection_error(self):
        """Test that fetch_page returns None on ConnectionError."""
        scraper = AWSScraper()

        # Mock session.get to always raise ConnectionError
        with patch.object(scraper.session, 'get', side_effect=ConnectionError("Connection failed")):
            with patch('time.sleep'):  # Don't actually sleep
                result = scraper.fetch_page("https://example.com")

        self.assertIsNone(result)

    def test_scraper_fetch_page_final_return_none(self):
        """Test that fetch_page returns None when all retries exhausted with different
        exceptions."""
        scraper = AWSScraper()

        # Mock to raise exception every time, ensuring we hit the final return None
        with patch.object(scraper.session, 'get') as mock_get:
            # Make it fail all 3 attempts with RequestException

            mock_get.side_effect = [
                requests.RequestException("Error 1"),
                requests.RequestException("Error 2"),
                requests.RequestException("Error 3")
            ]

            with patch('time.sleep'):  # Don't actually sleep
                result = scraper.fetch_page("https://example.com")

        # Should have tried 3 times
        self.assertEqual(mock_get.call_count, 3)
        self.assertIsNone(result)

    def test_internal_link_with_query_parameters(self):
        """Test rewriting internal links that have query parameters."""
        converter = AWSDocsToEpub(
            "https://docs.aws.amazon.com/msk/latest/developerguide/index.html")
        builder = EPUBBuilder("Test Guide", "AWS")

        # Add chapters with URLs
        chapter1 = builder.add_chapter(
            "API Reference",
            "<p>API content</p>",
            "https://docs.aws.amazon.com/msk/latest/developerguide/api.html?version=v1"
        )

        chapter2_content = """
        <p>See the <a href="https://docs.aws.amazon.com/msk/latest/developerguide/api.html?version=v1">API docs</a>.</p>
        """
        builder.add_chapter(
            "Guide",
            chapter2_content,
            "https://docs.aws.amazon.com/msk/latest/developerguide/guide.html"
        )

        # Rewrite internal links
        converter._rewrite_internal_links(  # pylint: disable=protected-access
            builder)

        # Parse the updated content

        soup = BeautifulSoup(builder.chapters[1].content, 'html.parser')
        link = soup.find('a')

        # Check that the link was rewritten
        assert link is not None
        self.assertEqual(link['href'], chapter1.file_name)

    def test_paste_icon_without_alpha(self):
        """Test pasting icon without transparency."""
        cover_img = Image.new('RGB', (100, 100), color='white')
        icon_img = Image.new('RGB', (50, 50), color='blue')

        # Should not raise an error
        _paste_icon(cover_img, icon_img, 10, 10)

        # Verify icon was pasted
        pixel = cover_img.getpixel((10, 10))
        self.assertEqual(pixel, (0, 0, 255))  # Blue color

    def test_paste_icon_with_alpha(self):
        """Test pasting icon with transparency."""
        cover_img = Image.new('RGB', (100, 100), color='white')
        icon_img = Image.new('RGBA', (50, 50), color=(0, 255, 0, 255))

        # Should not raise an error
        _paste_icon(cover_img, icon_img, 10, 10)

        # Verify icon was pasted
        pixel = cover_img.getpixel((10, 10))
        self.assertEqual(pixel, (0, 255, 0))  # Green color

    def test_split_text_with_very_long_title(self):
        """Test splitting very long text that doesn't fit even with smallest font."""
        # Create a test image and drawing context
        img = Image.new('RGB', (600, 100))
        draw = ImageDraw.Draw(img)

        # Very long text
        text = "A" * 200

        # Load a font
        font = _load_font(60)

        # This should handle the case where text is too long
        lines = _split_text_into_lines(text, font, draw, 500)

        # Should return some lines
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)

    def test_calculate_optimal_font_fallback_to_smallest(self):
        """Test that _calculate_optimal_font_and_text falls back to smallest font when text
        doesn't fit."""
        # Create a test image and drawing context
        img = Image.new('RGB', (200, 100))
        draw = ImageDraw.Draw(img)

        # Very long text that won't fit even with smallest font at any size
        text = "A" * 300

        # Very small available dimensions that will force fallback
        cover_width = 200
        cover_height = 100
        icon_height = 50

        # This should trigger the fallback to smallest font (60)
        font, lines = _calculate_optimal_font_and_text(
            text, draw, cover_width, cover_height, icon_height)

        # Verify we got a font and lines back
        self.assertIsNotNone(font)
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)

    def test_main_module_execution(self):
        """Test executing the package as a module."""
        # Test running: python -m aws_docs_to_epub --help
        result = subprocess.run(
            [sys.executable, '-m', 'aws_docs_to_epub', '--help'],
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )

        # Should exit with 0 and show help
        self.assertEqual(result.returncode, 0)
        self.assertIn('usage:', result.stdout.lower())

    def test_cli_as_main(self):
        """Test running cli.py directly as main."""
        # Test running the cli module directly
        result = subprocess.run(
            [sys.executable, '-m', 'aws_docs_to_epub.cli', '--help'],
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )

        # Should exit with 0 and show help
        self.assertEqual(result.returncode, 0)
        self.assertIn('usage:', result.stdout.lower())

    def test_commands_package_import(self):
        """Test that commands package can be imported."""

        # Verify __all__ is a list
        self.assertIsInstance(__all__, list)


if __name__ == '__main__':
    unittest.main()
