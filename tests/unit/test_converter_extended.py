"""Comprehensive unit tests for converter module."""

from unittest.mock import Mock, patch
import pytest


from aws_docs_to_epub.converter import AWSDocsToEpub, GuideConfig, GuideMetadata


def test_guide_config_dataclass():
    """Test GuideConfig dataclass creation."""
    config = GuideConfig(
        service_name="msk",
        version="latest",
        guide_type="developerguide",
        guide_path="/msk/latest/developerguide/",
        start_url="https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    )

    assert config.service_name == "msk"
    assert config.version == "latest"
    assert config.base_url == "https://docs.aws.amazon.com"


def test_guide_metadata_dataclass():
    """Test GuideMetadata dataclass creation."""
    metadata = GuideMetadata(title="Test Guide")

    assert metadata.title == "Test Guide"
    assert metadata.metadata == {}


def test_guide_metadata_post_init():
    """Test GuideMetadata post init."""
    metadata = GuideMetadata()

    assert metadata.title is None
    assert isinstance(metadata.metadata, dict)


def test_converter_init_valid_url():
    """Test converter initializes with valid URL."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    assert converter.config.service_name == "msk"
    assert converter.config.version == "latest"
    assert converter.config.guide_type == "developerguide"


def test_converter_init_with_cover_icon():
    """Test converter initialization with cover icon."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url, cover_icon_url="icon.png")

    assert converter.cover_icon_url == "icon.png"


def test_converter_init_invalid_url():
    """Test converter raises error with invalid URL."""
    url = "https://docs.aws.amazon.com/invalid"

    with pytest.raises(ValueError) as exc_info:
        AWSDocsToEpub(url)

    assert "Unable to parse" in str(exc_info.value)


def test_scrape_all_pages():
    """Test scraping all pages."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    mock_pages_info = [
        {'url': 'https://example.com/page1', 'title': 'Page 1'},
        {'url': 'https://example.com/page2', 'title': 'Page 2'}
    ]

    mock_scraped_pages = [
        {'title': 'Page 1', 'content': '<p>Content 1</p>',
            'url': 'url1', 'images': []},
        {'title': 'Page 2', 'content': '<p>Content 2</p>', 'url': 'url2', 'images': []}
    ]

    with patch.object(converter.toc_parser, 'load_toc', return_value=mock_pages_info):
        with patch.object(converter.scraper, 'fetch_page', return_value="<html></html>"):
            with patch.object(converter.scraper, 'extract_guide_title', return_value="Test Guide"):
                with patch.object(
                        converter.scraper, 'scrape_pages', return_value=mock_scraped_pages):
                    pages = converter.scrape_all_pages()

    assert len(pages) == 2
    assert converter.metadata.title == "Test Guide"


def test_scrape_all_pages_no_toc():
    """Test scraping when TOC is empty."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    with patch.object(converter.toc_parser, 'load_toc', return_value=[]):
        pages = converter.scrape_all_pages()

    assert len(pages) == 0


def test_scrape_all_pages_with_max_pages():
    """Test scraping with max_pages limit."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    mock_pages_info = [{'url': f'url{i}', 'title': f'Page {i}'}
                       for i in range(10)]

    with patch.object(converter.toc_parser, 'load_toc', return_value=mock_pages_info):
        with patch.object(converter.scraper, 'fetch_page', return_value="<html></html>"):
            with patch.object(converter.scraper, 'extract_guide_title', return_value="Test"):
                with patch.object(
                        converter.scraper, 'scrape_pages', return_value=[]) as mock_scrape:
                    converter.scrape_all_pages(max_pages=3)

    # scrape_pages should have been called
    assert mock_scrape.called
    # Check that the first argument (page_links) has only 3 items
    call_args = mock_scrape.call_args[0]
    assert len(call_args[0]) == 3


def test_create_epub():
    """Test creating EPUB from pages."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)
    converter.metadata.title = "Test Guide"

    pages = [
        {'title': 'Page 1', 'content': '<p>Content 1</p>',
            'url': 'url1', 'images': []},
    ]

    with patch('aws_docs_to_epub.converter.EPUBBuilder') as mock_builder_class:
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder

        with patch.object(converter, '_download_images', return_value={}):
            with patch.object(converter, '_add_chapter_with_images'):
                output = converter.create_epub(pages)

    assert output is not None
    mock_builder.add_css.assert_called_once()
    mock_builder.finalize.assert_called_once()
    mock_builder.write.assert_called_once()


def test_create_epub_no_pages():
    """Test creating EPUB with no pages returns None."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    output = converter.create_epub([])

    assert output is None


def test_create_epub_with_cover():
    """Test creating EPUB with cover image."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url, cover_icon_url="icon.png")
    converter.metadata.title = "Test Guide"

    pages = [{'title': 'Page 1', 'content': '<p>Content</p>',
              'url': 'url1', 'images': []}]

    with patch('aws_docs_to_epub.converter.EPUBBuilder') as mock_builder_class:
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder

        with patch.object(converter, '_download_images', return_value={}):
            with patch.object(converter, '_add_chapter_with_images'):
                converter.create_epub(pages)

    mock_builder.add_cover.assert_called_once_with("icon.png")


def test_create_epub_custom_filename():
    """Test creating EPUB with custom filename."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    pages = [{'title': 'Page 1', 'content': '<p>Content</p>',
              'url': 'url1', 'images': []}]

    with patch('aws_docs_to_epub.converter.EPUBBuilder') as mock_builder_class:
        mock_builder = Mock()
        mock_builder_class.return_value = mock_builder

        with patch.object(converter, '_download_images', return_value={}):
            with patch.object(converter, '_add_chapter_with_images'):
                output = converter.create_epub(pages, 'custom.epub')

    assert output == 'custom.epub'


def test_download_images():
    """Test downloading images for EPUB."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    pages = [
        {'title': 'Page 1', 'content': '', 'url': 'url1',
            'images': ['https://example.com/img1.png']},
        {'title': 'Page 2', 'content': '', 'url': 'url2',
            'images': ['https://example.com/img2.jpg']},
    ]

    mock_builder = Mock()

    with patch('aws_docs_to_epub.converter.fetch_image_from_url') as mock_fetch:
        mock_fetch.side_effect = [(b'img1data', 'png'), (b'img2data', 'jpg')]

        mapping = converter._download_images(  # pylint: disable=protected-access
            pages, mock_builder)
    assert len(mapping) == 2
    assert 'https://example.com/img1.png' in mapping
    assert 'https://example.com/img2.jpg' in mapping


def test_download_images_duplicate():
    """Test downloading same image only once."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    pages = [
        {'title': 'Page 1', 'content': '', 'url': 'url1',
            'images': ['https://example.com/img.png']},
        {'title': 'Page 2', 'content': '', 'url': 'url2',
            'images': ['https://example.com/img.png']},
    ]

    mock_builder = Mock()

    with patch('aws_docs_to_epub.converter.fetch_image_from_url') as mock_fetch:
        mock_fetch.return_value = (b'imgdata', 'png')

        mapping = converter._download_images(  # pylint: disable=protected-access
            pages, mock_builder)

    assert len(mapping) == 1
    assert mock_fetch.call_count == 1


def test_add_chapter_with_images():
    """Test adding chapter with image references."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    mock_builder = Mock()
    page = {
        'title': 'Test Page',
        'content': '<p><img src="https://example.com/img.png" /></p>',
        'url': 'url1',
        'images': []
    }
    image_mapping = {'https://example.com/img.png': 'images/img_0001.png'}

    converter._add_chapter_with_images(  # pylint: disable=protected-access
        mock_builder, page, image_mapping)

    mock_builder.add_chapter.assert_called_once()
    args = mock_builder.add_chapter.call_args[0]
    assert 'images/img_0001.png' in args[1]


def test_add_chapter_with_existing_h1():
    """Test adding chapter when content has matching h1."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    mock_builder = Mock()
    page = {
        'title': 'Test Page',
        'content': '<h1>Test Page</h1><p>Content</p>',
        'url': 'url1',
        'images': []
    }

    converter._add_chapter_with_images(  # pylint: disable=protected-access
        mock_builder, page, {})

    mock_builder.add_chapter.assert_called_once()
    args = mock_builder.add_chapter.call_args[0]
    # Should not duplicate h1
    assert args[1].count('<h1>') <= 1


def test_flatten_toc():
    """Test flattening hierarchical TOC structure."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    toc_structure = [
        {
            'url': 'https://example.com/page1.html',
            'title': 'Page 1',
            'children': [
                {'url': 'https://example.com/page2.html',
                    'title': 'Page 2', 'children': []},
                {'url': 'https://example.com/page3.html',
                    'title': 'Page 3', 'children': []}
            ]
        },
        {'url': 'https://example.com/page4.html',
            'title': 'Page 4', 'children': []}
    ]

    flat = converter._flatten_toc(  # pylint: disable=protected-access
        toc_structure)

    assert len(flat) == 4
    assert flat[0]['url'] == 'https://example.com/page1.html'
    assert flat[1]['url'] == 'https://example.com/page2.html'
    assert flat[2]['url'] == 'https://example.com/page3.html'
    assert flat[3]['url'] == 'https://example.com/page4.html'


def test_flatten_toc_deep_nesting():
    """Test flattening deeply nested TOC structure."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    toc_structure = [
        {
            'url': 'https://example.com/l1.html',
            'title': 'Level 1',
            'children': [
                {
                    'url': 'https://example.com/l2.html',
                    'title': 'Level 2',
                    'children': [
                        {'url': 'https://example.com/l3.html',
                            'title': 'Level 3', 'children': []}
                    ]
                }
            ]
        }
    ]

    flat = converter._flatten_toc(  # pylint: disable=protected-access
        toc_structure)

    assert len(flat) == 3
    assert flat[0]['title'] == 'Level 1'
    assert flat[1]['title'] == 'Level 2'
    assert flat[2]['title'] == 'Level 3'


def test_flatten_toc_with_no_url():
    """Test flattening TOC with entries that have no URL."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    toc_structure = [
        {
            'url': None,  # Section header with no page
            'title': 'Section',
            'children': [
                {'url': 'https://example.com/page1.html',
                    'title': 'Page 1', 'children': []},
                {'url': 'https://example.com/page2.html',
                    'title': 'Page 2', 'children': []}
            ]
        }
    ]

    flat = converter._flatten_toc(  # pylint: disable=protected-access
        toc_structure)

    # Should only include entries with URLs
    assert len(flat) == 2
    assert flat[0]['title'] == 'Page 1'
    assert flat[1]['title'] == 'Page 2'


def test_add_chapter_with_images_returns_chapter():
    """Test that _add_chapter_with_images returns the created chapter."""
    url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"
    converter = AWSDocsToEpub(url)

    mock_chapter = Mock()
    mock_builder = Mock()
    mock_builder.add_chapter.return_value = mock_chapter

    page = {
        'title': 'Test Page',
        'content': '<p>Content</p>',
        'url': 'https://example.com/test.html',
        'images': []
    }

    result = converter._add_chapter_with_images(  # pylint: disable=protected-access
        mock_builder, page, {})

    assert result == mock_chapter
    mock_builder.add_chapter.assert_called_once()
