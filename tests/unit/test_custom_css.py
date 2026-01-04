"""Tests for custom CSS feature."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from aws_docs_to_epub.core.epub_builder import EPUBBuilder


class TestCustomCSS(unittest.TestCase):
    """Test custom CSS override functionality."""

    def test_add_css_without_custom(self):
        """Test that add_css works without custom CSS (backwards compatibility)."""
        builder = EPUBBuilder("Test Guide")
        css_item = builder.add_css()

        # Should have default CSS only
        self.assertIn('@namespace epub', css_item.content)
        self.assertNotIn('/* Custom CSS Overrides */', css_item.content)

    def test_add_css_with_valid_custom_file(self):
        """Test adding custom CSS from a valid file."""
        builder = EPUBBuilder("Test Guide")

        # Create a temporary custom CSS file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False) as f:
            custom_css_path = f.name
            f.write("""
/* My custom styles */
body {
    font-size: 1.2em;
    background-color: #fff;
}

h1 {
    color: #ff0000;
}
""")

        try:
            css_item = builder.add_css(custom_css_path)

            # Should have both default and custom CSS
            self.assertIn('@namespace epub', css_item.content)
            self.assertIn('/* Custom CSS Overrides */', css_item.content)
            self.assertIn('/* My custom styles */', css_item.content)
            self.assertIn('background-color: #fff;', css_item.content)
            self.assertIn('color: #ff0000;', css_item.content)

            # Custom CSS should come after default CSS
            default_pos = css_item.content.find('@namespace epub')
            custom_pos = css_item.content.find('/* Custom CSS Overrides */')
            self.assertLess(default_pos, custom_pos)
        finally:
            # Clean up
            Path(custom_css_path).unlink()

    def test_add_css_with_nonexistent_file(self):
        """Test that add_css handles nonexistent custom CSS file gracefully."""
        builder = EPUBBuilder("Test Guide")

        # Try with a file that doesn't exist
        css_item = builder.add_css("/nonexistent/path/to/custom.css")

        # Should still have default CSS
        self.assertIn('@namespace epub', css_item.content)
        # Should not have custom CSS marker
        self.assertNotIn('/* Custom CSS Overrides */', css_item.content)

    def test_add_css_with_directory_path(self):
        """Test that add_css handles directory path gracefully."""
        builder = EPUBBuilder("Test Guide")

        # Try with a directory instead of a file
        with tempfile.TemporaryDirectory() as tmpdir:
            css_item = builder.add_css(tmpdir)

            # Should still have default CSS
            self.assertIn('@namespace epub', css_item.content)
            # Should not have custom CSS marker
            self.assertNotIn('/* Custom CSS Overrides */', css_item.content)

    def test_custom_css_overrides_default_styles(self):
        """Test that custom CSS can override default styles."""
        builder = EPUBBuilder("Test Guide")

        # Create custom CSS that overrides body font-size
        with tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False) as f:
            custom_css_path = f.name
            f.write("""
body {
    font-size: 2em !important;
}
""")

        try:
            css_item = builder.add_css(custom_css_path)

            # Check that both the default and override are present
            # The custom one comes later so it should override
            self.assertIn('font-size: 1em;', css_item.content)  # Default
            self.assertIn('font-size: 2em !important;',
                          css_item.content)  # Override

            # Verify order (custom comes after default)
            default_pos = css_item.content.find('font-size: 1em;')
            custom_pos = css_item.content.find('font-size: 2em !important;')
            self.assertLess(default_pos, custom_pos)
        finally:
            Path(custom_css_path).unlink()

    def test_custom_css_with_unicode_content(self):
        """Test that custom CSS handles unicode content correctly."""
        builder = EPUBBuilder("Test Guide")

        # Create custom CSS with unicode characters
        with tempfile.NamedTemporaryFile(
                mode='w', suffix='.css', delete=False, encoding='utf-8') as f:
            custom_css_path = f.name
            f.write("""
/* Custom styles with unicode: ñ, é, 中文 */
.special::before {
    content: "→";
}
""")

        try:
            css_item = builder.add_css(custom_css_path)

            # Should handle unicode correctly
            self.assertIn('中文', css_item.content)
            self.assertIn('→', css_item.content)
        finally:
            Path(custom_css_path).unlink()

    def test_custom_css_with_relative_path(self):
        """Test that custom CSS works with relative paths."""
        builder = EPUBBuilder("Test Guide")

        # Create a temporary file in the current directory
        temp_file = Path('temp_custom.css')
        try:
            temp_file.write_text('body { margin: 10%; }', encoding='utf-8')

            css_item = builder.add_css('temp_custom.css')

            # Should load the custom CSS
            self.assertIn('margin: 10%;', css_item.content)
            self.assertIn('/* Custom CSS Overrides */', css_item.content)
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_custom_css_with_io_error(self):
        """Test that add_css handles file reading errors gracefully."""

        builder = EPUBBuilder("Test Guide")

        # Create a file that will cause an error when opened
        temp_file = Path('error_test.css')
        try:
            temp_file.write_text('test', encoding='utf-8')

            # Make the file read-only and then try to open with write mode to simulate error
            # Or better, mock the specific custom CSS file open
            original_open = open

            def selective_open(*args, **kwargs):
                if args and 'error_test.css' in str(args[0]):
                    raise IOError("Permission denied")
                return original_open(*args, **kwargs)

            with patch('builtins.open', side_effect=selective_open):
                css_item = builder.add_css(str(temp_file))

                # Should still have default CSS
                self.assertIn('@namespace epub', css_item.content)
                # Should not have custom CSS marker
                self.assertNotIn('/* Custom CSS Overrides */',
                                 css_item.content)
        finally:
            if temp_file.exists():
                temp_file.unlink()
