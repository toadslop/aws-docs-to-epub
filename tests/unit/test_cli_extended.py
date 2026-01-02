"""Comprehensive unit tests for CLI module."""

from unittest.mock import Mock, patch
import pytest

from aws_docs_to_epub.cli import main


def test_cli_no_args():
    """Test CLI with no arguments shows help."""
    with pytest.raises(SystemExit):
        with patch('sys.argv', ['aws-docs-to-epub']):
            main()


def test_cli_invalid_url():
    """Test CLI with invalid URL exits with error."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['aws-docs-to-epub', 'https://invalid.com']):
            main()

    assert exc_info.value.code == 1


def test_cli_converter_init_error():
    """Test CLI handles converter initialization error."""
    with pytest.raises(SystemExit):
        with patch('sys.argv', ['aws-docs-to-epub', 'https://docs.aws.amazon.com/test']):
            main()


def test_cli_successful_conversion():
    """Test successful conversion flow."""
    test_url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"

    mock_converter = Mock()
    mock_converter.config = Mock()
    mock_converter.config.service_name = "msk"
    mock_converter.config.guide_type = "developerguide"
    mock_converter.metadata = Mock()
    mock_converter.metadata.title = "AWS MSK Developer Guide"
    mock_converter.scrape_all_pages.return_value = [
        {'title': 'Page 1', 'content': '<p>Content</p>', 'url': 'url1', 'images': []}
    ]
    mock_converter.create_epub.return_value = "test.epub"

    with patch('sys.argv', ['aws-docs-to-epub', test_url]):
        with patch('aws_docs_to_epub.cli.AWSDocsToEpub', return_value=mock_converter):
            main()

    mock_converter.scrape_all_pages.assert_called_once()
    mock_converter.create_epub.assert_called_once()


def test_cli_no_pages_scraped():
    """Test CLI handles case when no pages are scraped."""
    test_url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"

    mock_converter = Mock()
    mock_converter.config = Mock()
    mock_converter.config.service_name = "msk"
    mock_converter.config.guide_type = "developerguide"
    mock_converter.scrape_all_pages.return_value = []

    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['aws-docs-to-epub', test_url]):
            with patch('aws_docs_to_epub.cli.AWSDocsToEpub', return_value=mock_converter):
                main()

    assert exc_info.value.code == 1


def test_cli_epub_creation_failure():
    """Test CLI handles EPUB creation failure."""
    test_url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"

    mock_converter = Mock()
    mock_converter.config = Mock()
    mock_converter.config.service_name = "msk"
    mock_converter.config.guide_type = "developerguide"
    mock_converter.metadata = Mock()
    mock_converter.metadata.title = "Test Guide"
    mock_converter.scrape_all_pages.return_value = [{'title': 'Page 1'}]
    mock_converter.create_epub.return_value = None

    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['aws-docs-to-epub', test_url]):
            with patch('aws_docs_to_epub.cli.AWSDocsToEpub', return_value=mock_converter):
                main()

    assert exc_info.value.code == 1


def test_cli_with_custom_output():
    """Test CLI with custom output filename."""
    test_url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"

    mock_converter = Mock()
    mock_converter.config = Mock()
    mock_converter.config.service_name = "msk"
    mock_converter.config.guide_type = "developerguide"
    mock_converter.metadata = Mock()
    mock_converter.metadata.title = "Test Guide"
    mock_converter.scrape_all_pages.return_value = [{'title': 'Page 1'}]
    mock_converter.create_epub.return_value = "custom.epub"

    with patch('sys.argv', ['aws-docs-to-epub', test_url, '-o', 'custom.epub']):
        with patch('aws_docs_to_epub.cli.AWSDocsToEpub', return_value=mock_converter):
            main()

    # Check that create_epub was called with pages and custom filename
    mock_converter.create_epub.assert_called_once_with(
        [{'title': 'Page 1'}], 'custom.epub')


def test_cli_with_cover_icon():
    """Test CLI with cover icon option."""
    test_url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"

    mock_converter = Mock()
    mock_converter.config = Mock()
    mock_converter.config.service_name = "msk"
    mock_converter.config.guide_type = "developerguide"
    mock_converter.metadata = Mock()
    mock_converter.metadata.title = "Test Guide"
    mock_converter.scrape_all_pages.return_value = [{'title': 'Page 1'}]
    mock_converter.create_epub.return_value = "test.epub"

    with patch('sys.argv', ['aws-docs-to-epub', test_url, '-c', 'icon.png']):
        with patch('aws_docs_to_epub.cli.AWSDocsToEpub') as mock_class:
            mock_class.return_value = mock_converter
            main()

    # Check that converter was initialized with cover icon
    mock_class.assert_called_with(test_url, 'icon.png')


def test_cli_with_max_pages():
    """Test CLI with max pages option."""
    test_url = "https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html"

    mock_converter = Mock()
    mock_converter.config = Mock()
    mock_converter.config.service_name = "msk"
    mock_converter.config.guide_type = "developerguide"
    mock_converter.metadata = Mock()
    mock_converter.metadata.title = "Test Guide"
    mock_converter.scrape_all_pages.return_value = [{'title': 'Page 1'}]
    mock_converter.create_epub.return_value = "test.epub"

    with patch('sys.argv', ['aws-docs-to-epub', test_url, '--max-pages', '5']):
        with patch('aws_docs_to_epub.cli.AWSDocsToEpub', return_value=mock_converter):
            main()

    # Check that scrape_all_pages was called with max_pages
    mock_converter.scrape_all_pages.assert_called_with(max_pages=5)


def test_cli_version():
    """Test CLI --version option."""
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['aws-docs-to-epub', '--version']):
            main()

    assert exc_info.value.code == 0
