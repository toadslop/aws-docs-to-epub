"""Tests for internal link rewriting functionality."""

import unittest
from bs4 import BeautifulSoup

from aws_docs_to_epub.converter import AWSDocsToEpub
from aws_docs_to_epub.core.epub_builder import EPUBBuilder


class TestInternalLinkRewriting(unittest.TestCase):
    """Test suite for internal link rewriting."""

    def test_url_to_filename_mapping(self):
        """Test that URL to filename mapping is tracked correctly."""
        builder = EPUBBuilder("Test Guide", "AWS")

        # Add a chapter with a source URL
        chapter = builder.add_chapter(
            "Test Chapter",
            "<p>Test content</p>",
            "https://docs.aws.amazon.com/service/latest/guide/test.html"
        )

        # Verify mapping was created
        self.assertIn("https://docs.aws.amazon.com/service/latest/guide/test.html",
                      builder.url_to_filename)
        self.assertEqual(
            builder.url_to_filename["https://docs.aws.amazon.com/service/latest/guide/test.html"],
            chapter.file_name
        )

    def test_internal_link_rewriting(self):
        """Test that internal links are rewritten correctly."""
        # Create converter instance
        converter = AWSDocsToEpub(
            "https://docs.aws.amazon.com/msk/latest/developerguide/index.html")

        # Create builder
        builder = EPUBBuilder("Test Guide", "AWS")

        # Add chapters with URLs
        chapter1 = builder.add_chapter(
            "Introduction",
            "<p>Introduction content</p>",
            "https://docs.aws.amazon.com/msk/latest/developerguide/intro.html"
        )

        chapter2_content = """
        <p>See the <a href="https://docs.aws.amazon.com/msk/latest/developerguide/intro.html">introduction</a> 
        for more info.</p>
        <p>Also check out <a href="https://docs.aws.amazon.com/lambda/latest/dg/intro.html">Lambda docs</a>.</p>
        <p>And <a href="https://example.com">external link</a>.</p>
        """
        builder.add_chapter(
            "Getting Started",
            chapter2_content,
            "https://docs.aws.amazon.com/msk/latest/developerguide/getting-started.html"
        )

        # Rewrite internal links
        converter._rewrite_internal_links(  # pylint: disable=protected-access
            builder)

        # Parse the updated content
        soup = BeautifulSoup(builder.chapters[1].content, 'html.parser')
        links = soup.find_all('a')

        # Check that internal link was rewritten
        internal_link = links[0]
        self.assertEqual(internal_link['href'], chapter1.file_name)

        # Check that external AWS link (different service) was NOT rewritten
        lambda_link = links[1]
        self.assertEqual(lambda_link['href'],
                         "https://docs.aws.amazon.com/lambda/latest/dg/intro.html")

        # Check that external link was NOT rewritten
        external_link = links[2]
        self.assertEqual(external_link['href'], "https://example.com")

    def test_internal_link_with_fragment(self):
        """Test that internal links with fragments preserve the fragment."""
        converter = AWSDocsToEpub(
            "https://docs.aws.amazon.com/msk/latest/developerguide/index.html")
        builder = EPUBBuilder("Test Guide", "AWS")

        # Add chapters
        chapter1 = builder.add_chapter(
            "API Reference",
            "<h2 id='method1'>Method 1</h2><p>Content</p>",
            "https://docs.aws.amazon.com/msk/latest/developerguide/api.html"
        )

        chapter2_content = """
        <p>See <a href="https://docs.aws.amazon.com/msk/latest/developerguide/api.html#method1">Method 1</a>.</p>
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

        # Check that the link has both filename and fragment
        expected_href = f"{chapter1.file_name}#method1"
        assert link is not None
        self.assertEqual(link['href'], expected_href)


if __name__ == '__main__':
    unittest.main()
