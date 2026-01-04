"""Tests for CSS asset loading."""

import unittest
from pathlib import Path

from aws_docs_to_epub.core.epub_builder import EPUBBuilder


class TestCSSAssets(unittest.TestCase):
    """Test CSS asset loading from external file."""

    def test_css_file_exists(self):
        """Test that the CSS file exists in the assets directory."""
        css_file = Path(__file__).parent.parent.parent / 'src' / \
            'aws_docs_to_epub' / 'assets' / 'epub_styles.css'
        self.assertTrue(css_file.exists(), f"CSS file not found at {css_file}")

    def test_add_css_loads_from_file(self):
        """Test that add_css() loads CSS from external file."""
        builder = EPUBBuilder("Test Guide")
        css_item = builder.add_css()

        # Verify CSS was loaded
        self.assertIsNotNone(css_item)
        self.assertIsNotNone(css_item.content)

        # Verify it's actual CSS content
        content = css_item.content
        self.assertIn('@namespace epub', content)
        self.assertIn('body {', content)
        self.assertIn('font-family:', content)

        # Verify reasonable length (should be around 2-3KB)
        self.assertGreater(len(content), 2000)
        self.assertLess(len(content), 5000)

    def test_css_item_properties(self):
        """Test that CSS item has correct properties."""
        builder = EPUBBuilder("Test Guide")
        css_item = builder.add_css()

        self.assertEqual(css_item.id, "style_main")
        builder = EPUBBuilder("Test Guide")
        css_item = builder.add_css()
        content = css_item.content

        # Check for heading styles
        for heading in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.assertIn(heading, content, f"Missing {heading} style")

        # Check for important element styles
        for element in ['body', 'p', 'pre', 'code', 'table', 'img', 'a']:
            self.assertIn(element, content, f"Missing {element} style")

        # Check for specific style rules
        self.assertIn('pre.programlisting', content)
        self.assertIn('p code', content)


if __name__ == '__main__':
    unittest.main()
