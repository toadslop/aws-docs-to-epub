"""Comprehensive unit tests for TOC parser module."""

from unittest.mock import Mock, patch, mock_open
import json
import pytest
import requests

from aws_docs_to_epub.core.toc_parser import TOCParser

# pylint: disable=redefined-outer-name


@pytest.fixture
def mock_session():
    """Create a mock requests session."""
    return Mock(spec=requests.Session)


@pytest.fixture
def toc_parser(mock_session):
    """Create a TOC parser instance."""
    return TOCParser(mock_session, "https://docs.aws.amazon.com", "/service/latest/guide/")


def test_toc_parser_init(toc_parser, mock_session):
    """Test TOC parser initialization."""
    assert toc_parser.session == mock_session
    assert toc_parser.base_url == "https://docs.aws.amazon.com"
    assert toc_parser.guide_path == "/service/latest/guide/"
    assert isinstance(toc_parser.visited_urls, set)


def test_fetch_toc_json_success(toc_parser):
    """Test successful TOC JSON fetch."""
    mock_response = Mock()
    mock_response.json.return_value = {"title": "Test", "contents": []}

    with patch.object(toc_parser.session, 'get', return_value=mock_response):
        result = toc_parser.fetch_toc_json()

        assert result == {"title": "Test", "contents": []}
        toc_parser.session.get.assert_called_once()


def test_fetch_toc_json_failure(toc_parser):
    """Test TOC JSON fetch failure."""
    with patch.object(toc_parser.session, 'get', side_effect=requests.RequestException("Error")):
        result = toc_parser.fetch_toc_json()

        assert result is None


def test_fetch_toc_json_invalid_json(toc_parser):
    """Test TOC JSON fetch with invalid JSON."""
    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")

    with patch.object(toc_parser.session, 'get', return_value=mock_response):
        result = toc_parser.fetch_toc_json()

        assert result is None


def test_parse_toc_json_dict_with_href(toc_parser):
    """Test parsing TOC JSON dictionary with href."""
    toc_data = {
        "title": "Introduction",
        "href": "intro.html"
    }

    pages = toc_parser.parse_toc_json(toc_data)

    assert len(pages) == 1
    assert pages[0]['title'] == "Introduction"
    assert "intro.html" in pages[0]['url']


def test_parse_toc_json_skips_pdf(toc_parser):
    """Test parsing TOC JSON skips PDF links."""
    toc_data = {
        "title": "PDF Guide",
        "href": "guide.pdf"
    }

    pages = toc_parser.parse_toc_json(toc_data)

    assert len(pages) == 0


def test_parse_toc_json_nested_contents(toc_parser):
    """Test parsing nested TOC contents with hierarchy."""
    toc_data = {
        "title": "Main",
        "href": "main.html",
        "contents": [
            {"title": "Sub 1", "href": "sub1.html"},
            {"title": "Sub 2", "href": "sub2.html"}
        ]
    }

    pages = toc_parser.parse_toc_json(toc_data)

    # Now returns hierarchical structure
    assert len(pages) == 1  # One parent entry
    assert pages[0]['title'] == "Main"
    assert len(pages[0]['children']) == 2  # Two child entries
    assert pages[0]['children'][0]['title'] == "Sub 1"
    assert pages[0]['children'][1]['title'] == "Sub 2"


def test_parse_toc_json_list(toc_parser):
    """Test parsing TOC JSON as list."""
    toc_data = [
        {"title": "Page 1", "href": "page1.html"},
        {"title": "Page 2", "href": "page2.html"}
    ]

    pages = toc_parser.parse_toc_json(toc_data)

    assert len(pages) == 2


def test_parse_toc_json_no_duplicate_urls(toc_parser):
    """Test parsing doesn't add duplicate URLs."""
    toc_data = [
        {"title": "Page", "href": "page.html"},
        {"title": "Page", "href": "page.html"}
    ]

    pages = toc_parser.parse_toc_json(toc_data)

    assert len(pages) == 1


def test_load_toc_from_file(toc_parser):
    """Test loading TOC from file."""
    toc_data = {"title": "Test", "href": "test.html"}
    mock_file_content = json.dumps(toc_data)

    with patch('builtins.open', mock_open(read_data=mock_file_content)):
        with patch('os.path.exists', return_value=True):
            pages = toc_parser.load_toc('test.json')

    assert len(pages) == 1


def test_load_toc_from_url(toc_parser):
    """Test loading TOC from URL."""
    toc_data = {"title": "Test", "href": "test.html"}

    with patch.object(toc_parser, 'fetch_toc_json', return_value=toc_data):
        pages = toc_parser.load_toc()

    assert len(pages) == 1


def test_load_toc_fetch_failure(toc_parser):
    """Test loading TOC when fetch fails."""
    with patch.object(toc_parser, 'fetch_toc_json', return_value=None):
        pages = toc_parser.load_toc()

    assert len(pages) == 0


def test_load_toc_file_error(toc_parser):
    """Test loading TOC handles file errors."""
    with patch('builtins.open', side_effect=OSError("File error")):
        with patch('os.path.exists', return_value=True):
            pages = toc_parser.load_toc('test.json')

    assert len(pages) == 0


def test_load_toc_json_decode_error(toc_parser):
    """Test loading TOC handles JSON decode errors."""
    with patch('builtins.open', mock_open(read_data='invalid json')):
        with patch('os.path.exists', return_value=True):
            pages = toc_parser.load_toc('test.json')

    assert len(pages) == 0
