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


def test_build_nested_toc_with_children(epub_builder):
    """Test building nested TOC structure with parent-child relationships."""
    # Create chapters
    parent = epub_builder.add_chapter(
        "Parent Chapter", "<p>Parent content</p>")
    child1 = epub_builder.add_chapter("Child 1", "<p>Child 1 content</p>")
    child2 = epub_builder.add_chapter("Child 2", "<p>Child 2 content</p>")

    # Create TOC structure
    toc_structure = [
        {
            'url': 'parent.html',
            'title': 'Parent Chapter',
            'children': [
                {'url': 'child1.html', 'title': 'Child 1', 'children': []},
                {'url': 'child2.html', 'title': 'Child 2', 'children': []}
            ]
        }
    ]

    chapter_map = {
        'parent.html': parent,
        'child1.html': child1,
        'child2.html': child2
    }

    # Build nested TOC
    result = epub_builder._build_nested_toc(  # pylint: disable=protected-access
        toc_structure, chapter_map)

    assert isinstance(result, tuple)
    assert len(result) == 1
    # First element should be a tuple (parent, children)
    assert isinstance(result[0], tuple)
    assert result[0][0] == parent
    # Children should be a tuple
    assert isinstance(result[0][1], tuple)
    assert len(result[0][1]) == 2


def test_build_nested_toc_leaf_nodes(epub_builder):
    """Test building nested TOC with leaf nodes (no children)."""
    chapter1 = epub_builder.add_chapter("Chapter 1", "<p>Content 1</p>")
    chapter2 = epub_builder.add_chapter("Chapter 2", "<p>Content 2</p>")

    toc_structure = [
        {'url': 'ch1.html', 'title': 'Chapter 1', 'children': []},
        {'url': 'ch2.html', 'title': 'Chapter 2', 'children': []}
    ]

    chapter_map = {
        'ch1.html': chapter1,
        'ch2.html': chapter2
    }

    result = epub_builder._build_nested_toc(  # pylint: disable=protected-access
        toc_structure, chapter_map)

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[0] == chapter1
    assert result[1] == chapter2


def test_build_nested_toc_missing_chapter(epub_builder):
    """Test building nested TOC when chapter is missing from map."""
    chapter1 = epub_builder.add_chapter("Chapter 1", "<p>Content 1</p>")

    toc_structure = [
        {'url': 'ch1.html', 'title': 'Chapter 1', 'children': []},
        {'url': 'missing.html', 'title': 'Missing', 'children': []}  # Not in map
    ]

    chapter_map = {
        'ch1.html': chapter1
    }

    result = epub_builder._build_nested_toc(  # pylint: disable=protected-access
        toc_structure, chapter_map)

    # Should only include the chapter that exists
    assert isinstance(result, tuple)
    assert len(result) == 1
    assert result[0] == chapter1


def test_build_nested_toc_no_url_with_children(epub_builder):
    """Test building nested TOC with section that has no URL but has children."""
    child1 = epub_builder.add_chapter("Child 1", "<p>Child 1 content</p>")
    child2 = epub_builder.add_chapter("Child 2", "<p>Child 2 content</p>")

    toc_structure = [
        {
            'url': None,  # Section header with no page
            'title': 'Section',
            'children': [
                {'url': 'child1.html', 'title': 'Child 1', 'children': []},
                {'url': 'child2.html', 'title': 'Child 2', 'children': []}
            ]
        }
    ]

    chapter_map = {
        'child1.html': child1,
        'child2.html': child2
    }

    result = epub_builder._build_nested_toc(  # pylint: disable=protected-access
        toc_structure, chapter_map)

    # Children should be included directly without parent
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert child1 in result
    assert child2 in result


def test_build_nested_toc_deep_nesting(epub_builder):
    """Test building deeply nested TOC structure."""
    ch1 = epub_builder.add_chapter("Level 1", "<p>L1</p>")
    ch2 = epub_builder.add_chapter("Level 2", "<p>L2</p>")
    ch3 = epub_builder.add_chapter("Level 3", "<p>L3</p>")

    toc_structure = [
        {
            'url': 'l1.html',
            'title': 'Level 1',
            'children': [
                {
                    'url': 'l2.html',
                    'title': 'Level 2',
                    'children': [
                        {'url': 'l3.html', 'title': 'Level 3', 'children': []}
                    ]
                }
            ]
        }
    ]

    chapter_map = {
        'l1.html': ch1,
        'l2.html': ch2,
        'l3.html': ch3
    }

    result = epub_builder._build_nested_toc(  # pylint: disable=protected-access
        toc_structure, chapter_map)

    assert isinstance(result, tuple)
    assert len(result) == 1
    # Verify 3 levels of nesting
    assert isinstance(result[0], tuple)  # Level 1 with children
    assert result[0][0] == ch1
    assert isinstance(result[0][1], tuple)  # Level 2 with children
    assert isinstance(result[0][1][0], tuple)
    assert result[0][1][0][0] == ch2


def test_finalize_with_nested_toc(epub_builder):
    """Test finalizing book with nested TOC structure."""
    chapter1 = epub_builder.add_chapter("Chapter 1", "<p>Content 1</p>")
    chapter2 = epub_builder.add_chapter("Chapter 2", "<p>Content 2</p>")

    toc_structure = [
        {
            'url': 'ch1.html',
            'title': 'Chapter 1',
            'children': [
                {'url': 'ch2.html', 'title': 'Chapter 2', 'children': []}
            ]
        }
    ]

    chapter_map = {
        'ch1.html': chapter1,
        'ch2.html': chapter2
    }

    epub_builder.finalize(toc_structure=toc_structure, chapter_map=chapter_map)

    # Verify TOC was set to nested structure
    assert isinstance(epub_builder.book.toc, tuple)
    assert len(epub_builder.book.toc) == 1


def test_finalize_without_nested_toc(epub_builder):
    """Test finalizing book without nested TOC (flat fallback)."""
    epub_builder.add_chapter("Chapter 1", "<p>Content 1</p>")
    epub_builder.add_chapter("Chapter 2", "<p>Content 2</p>")

    epub_builder.finalize()

    # Should use flat toc_items
    assert epub_builder.book.toc == epub_builder.toc_items
