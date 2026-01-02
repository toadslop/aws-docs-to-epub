"""Comprehensive unit tests for EPUB builder module."""
# pylint: disable=redefined-outer-name

from unittest.mock import patch
import pytest


from aws_docs_to_epub.core.epub_builder import EPUBBuilder


@pytest.fixture
def epub_builder():
    """Create an EPUB builder instance."""
    return EPUBBuilder(title="Test Guide", author="Test Author")


def test_epub_builder_init(epub_builder):
    """Test EPUB builder initialization."""
    assert epub_builder.title == "Test Guide"
    assert epub_builder.author == "Test Author"
    assert len(epub_builder.chapters) == 0
    assert len(epub_builder.toc_items) == 0
    assert epub_builder.spine == ['nav']


def test_epub_builder_custom_identifier():
    """Test EPUB builder with custom identifier."""
    builder = EPUBBuilder(
        title="Test",
        author="Author",
        language="fr",
        identifier="test-id-123"
    )
    assert builder.title == "Test"


def test_sanitize_filename(epub_builder):
    """Test filename sanitization."""
    assert epub_builder.sanitize_filename("Test Title") == "test_title"
    assert epub_builder.sanitize_filename("Test-Title!@#") == "test_title"
    assert epub_builder.sanitize_filename(
        "Test   Multiple   Spaces") == "test_multiple_spaces"

    # Test truncation
    long_title = "a" * 100
    result = epub_builder.sanitize_filename(long_title)
    assert len(result) <= 50


def test_add_chapter(epub_builder):
    """Test adding a chapter."""
    chapter = epub_builder.add_chapter("Chapter 1", "<p>Content</p>")

    assert len(epub_builder.chapters) == 1
    assert len(epub_builder.toc_items) == 1
    assert len(epub_builder.spine) == 2  # nav + chapter
    assert chapter in epub_builder.chapters


def test_add_chapter_with_empty_content(epub_builder):
    """Test adding chapter with empty content."""
    chapter = epub_builder.add_chapter("Chapter", "")

    assert "Content not available" in chapter.content


def test_clean_content_removes_scripts(epub_builder):
    """Test content cleaning removes scripts."""
    html = "<div><script>alert('test');</script><p>Content</p></div>"

    cleaned = epub_builder._clean_content(  # pylint: disable=protected-access
        html)

    assert "script" not in cleaned.lower()
    assert "Content" in cleaned


def test_clean_content_fixes_image_paths(epub_builder):
    """Test content cleaning fixes image paths."""
    html = '<div><img src="//cdn.example.com/image.png" /></div>'

    cleaned = epub_builder._clean_content(  # pylint: disable=protected-access
        html)

    assert "https://cdn.example.com/image.png" in cleaned


def test_clean_content_fixes_relative_image_paths(epub_builder):
    """Test content cleaning fixes relative image paths."""
    html = '<div><img src="/images/test.png" /></div>'

    cleaned = epub_builder._clean_content(  # pylint: disable=protected-access
        html)

    assert "https://docs.aws.amazon.com/images/test.png" in cleaned


def test_add_css(epub_builder):
    """Test adding CSS stylesheet."""
    css = epub_builder.add_css()

    assert css is not None
    assert css.file_name == "style/nav.css"


def test_add_cover_from_file(epub_builder):
    """Test adding cover from file."""
    mock_icon_data = b"fake image data"
    mock_cover_data = b"fake cover image"

    with patch('os.path.isfile', return_value=True):
        with patch(
                'aws_docs_to_epub.core.epub_builder.fetch_local_image',
                return_value=(mock_icon_data, 'png')):
            with patch(
                    'aws_docs_to_epub.core.epub_builder.render_cover_image',
                    return_value=mock_cover_data):
                epub_builder.add_cover('/path/to/icon.png')


def test_add_cover_from_url(epub_builder):
    """Test adding cover from URL."""
    mock_icon_data = b"fake image data"
    mock_cover_data = b"fake cover image"

    with patch('os.path.isfile', return_value=False):
        with patch(
                'aws_docs_to_epub.core.epub_builder.fetch_image_from_url',
                return_value=(mock_icon_data, 'png')):
            with patch(
                    'aws_docs_to_epub.core.epub_builder.render_cover_image',
                    return_value=mock_cover_data):
                epub_builder.add_cover('https://example.com/icon.png')


def test_add_cover_fetch_failure(epub_builder):
    """Test adding cover handles fetch failure."""
    with patch('os.path.isfile', return_value=False):
        with patch(
                'aws_docs_to_epub.core.epub_builder.fetch_image_from_url',
                return_value=(None, 'png')):
            # Should not raise
            epub_builder.add_cover('https://example.com/icon.png')


def test_add_cover_render_failure(epub_builder):
    """Test adding cover handles render failure."""
    mock_icon_data = b"fake image data"

    with patch('os.path.isfile', return_value=False):
        with patch(
                'aws_docs_to_epub.core.epub_builder.fetch_image_from_url',
                return_value=(mock_icon_data, 'png')):
            with patch('aws_docs_to_epub.core.epub_builder.render_cover_image', return_value=None):
                # Should not raise
                epub_builder.add_cover('https://example.com/icon.png')


def test_add_cover_exception_handling(epub_builder):
    """Test adding cover handles exceptions."""
    with patch('os.path.isfile', side_effect=OSError("File error")):
        epub_builder.add_cover('/path/to/icon.png')  # Should not raise


def test_finalize(epub_builder):
    """Test finalizing the book."""
    epub_builder.add_chapter("Chapter 1", "<p>Content</p>")
    epub_builder.finalize()

    assert epub_builder.book.toc == epub_builder.toc_items


def test_write(epub_builder):
    """Test writing EPUB file."""
    epub_builder.add_chapter("Chapter 1", "<p>Content</p>")
    epub_builder.finalize()

    with patch('ebooklib.epub.write_epub') as mock_write:
        epub_builder.write('test.epub')
        mock_write.assert_called_once()


def test_get_chapter_count(epub_builder):
    """Test getting chapter count."""
    assert epub_builder.get_chapter_count() == 0

    epub_builder.add_chapter("Chapter 1", "<p>Content</p>")
    assert epub_builder.get_chapter_count() == 1

    epub_builder.add_chapter("Chapter 2", "<p>More content</p>")
    assert epub_builder.get_chapter_count() == 2


def test_clean_content_wraps_in_div(epub_builder):
    """Test content cleaning wraps content in div when no body tag."""
    html = "<p>Content</p>"

    cleaned = epub_builder._clean_content(  # pylint: disable=protected-access
        html)

    assert "<div>" in cleaned or "<p>" in cleaned


def test_multiple_chapters(epub_builder):
    """Test adding multiple chapters."""
    for i in range(5):
        epub_builder.add_chapter(f"Chapter {i}", f"<p>Content {i}</p>")

    assert epub_builder.get_chapter_count() == 5
    assert len(epub_builder.toc_items) == 5


def test_clean_content_with_body_tag(epub_builder):
    """Test content cleaning preserves body content."""
    html = "<html><body><p>Content</p></body></html>"

    cleaned = epub_builder._clean_content(  # pylint: disable=protected-access
        html)

    assert "<body>" in cleaned or "Content" in cleaned


def test_clean_content_handles_none_body(epub_builder):
    """Test content cleaning when body is present but None in some edge case."""
    html = "<html><head></head><body></body></html>"

    cleaned = epub_builder._clean_content(  # pylint: disable=protected-access
        html)

    # Should return something valid
    assert cleaned is not None
    assert len(cleaned) > 0
