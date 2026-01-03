"""Comprehensive unit tests for create_scraper module."""  # pylint: disable=redefined-outer-name
from unittest.mock import Mock, patch
import pytest
from bs4 import BeautifulSoup
import requests

from aws_docs_to_epub.core.scraper import AWSScraper

# pylint: disable=redefined-outer-name


@pytest.fixture
def create_scraper():
    """Create a create_scraper instance."""
    return AWSScraper()


def test_scraper_init(create_scraper):
    """Test create_scraper initialization."""
    assert isinstance(create_scraper.session, requests.Session)
    assert create_scraper.session.headers['User-Agent']
    assert isinstance(create_scraper.visited_urls, set)
    assert len(create_scraper.visited_urls) == 0


def test_fetch_page_success(create_scraper):
    """Test successful page fetch."""
    mock_response = Mock()
    mock_response.text = "<html><body>Test</body></html>"
    mock_response.encoding = "utf-8"

    with patch.object(create_scraper.session, 'get', return_value=mock_response):
        result = create_scraper.fetch_page("https://example.com")
        assert result == "<html><body>Test</body></html>"


def test_fetch_page_failure(create_scraper):
    """Test page fetch failure with retries."""
    with patch.object(
            create_scraper.session, 'get', side_effect=requests.RequestException("Error")):
        with patch('time.sleep'):  # Don't actually sleep in tests
            result = create_scraper.fetch_page("https://example.com")
            assert result is None


def test_extract_content_success(create_scraper):
    """Test content extraction from HTML."""
    html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Test Title</h1>
            <main>
                <p>Test content</p>
                <img src="/image.png" />
            </main>
        </body>
    </html>
    """
    url = "https://docs.aws.amazon.com/test/page.html"

    result = create_scraper.extract_content(html, url)

    assert result is not None
    assert result['title'] == "Test Title"
    assert result['url'] == url
    assert 'Test content' in result['content']
    assert len(result['images']) > 0


def test_extract_content_no_main(create_scraper):
    """Test content extraction when no main tag exists."""
    html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
    url = "https://example.com"

    result = create_scraper.extract_content(html, url)

    assert result is not None
    assert result['title'] == "Title"


def test_extract_title(create_scraper):
    """Test title extraction."""
    html = "<html><body><h1>My Title</h1></body></html>"
    soup = BeautifulSoup(html, 'lxml')

    title = create_scraper._extract_title(  # pylint: disable=protected-access
        soup)

    assert title == "My Title"


def test_extract_title_fallback(create_scraper):
    """Test title extraction fallback to title tag."""
    html = "<html><head><title>Fallback Title</title></head><body></body></html>"
    soup = BeautifulSoup(html, 'lxml')

    title = create_scraper._extract_title(  # pylint: disable=protected-access

        soup)
    assert title == "Fallback Title"


def test_extract_title_no_title(create_scraper):
    """Test title extraction when no title exists."""
    html = "<html><body></body></html>"
    soup = BeautifulSoup(html, 'lxml')

    title = create_scraper._extract_title(  # pylint: disable=protected-access
        soup)

    assert title == "Untitled"


def test_clean_content(create_scraper):
    """Test content cleaning removes unwanted elements."""
    html = """
    <div>
        <script>alert('test');</script>
        <style>.test{}</style>
        <nav>Navigation</nav>
        <p>Content</p>
    </div>
    """
    soup = BeautifulSoup(html, 'lxml')
    main_content = soup.find('div')

    create_scraper._clean_content(  # pylint: disable=protected-access
        main_content)

    assert main_content is not None
    assert main_content.find('script') is None
    assert main_content.find('style') is None
    assert main_content.find('nav') is None
    assert main_content.find('p') is not None


def test_fix_links_and_images(create_scraper):
    """Test fixing relative URLs."""
    html = '<div><a href="/relative">Link</a><img src="/image.png" /></div>'
    soup = BeautifulSoup(html, 'lxml')
    main_content = soup.find('div')
    base_url = "https://docs.aws.amazon.com/guide/page.html"

    create_scraper._fix_links_and_images(  # pylint: disable=protected-access
        main_content, base_url)

    assert main_content is not None
    link = main_content.find('a')
    img = main_content.find('img')
    assert link is not None
    assert img is not None
    assert link['href'] == "https://docs.aws.amazon.com/relative"
    assert img['src'] == "https://docs.aws.amazon.com/image.png"


def test_scrape_pages(create_scraper):
    """Test scraping multiple pages."""
    page_links = [
        {'url': 'https://example.com/1', 'title': 'Page 1'},
        {'url': 'https://example.com/2', 'title': 'Page 2'}
    ]

    mock_html = "<html><body><h1>Test</h1><main><p>Content</p></main></body></html>"

    with patch.object(create_scraper, 'fetch_page', return_value=mock_html):
        with patch('time.sleep'):  # Don't sleep in tests
            pages = create_scraper.scrape_pages(page_links)

    assert len(pages) == 2
    assert all('title' in page for page in pages)


def test_scrape_pages_with_max_pages(create_scraper):
    """Test scraping with max_pages limit."""
    page_links = [{'url': f'https://example.com/{i}',
                   'title': f'Page {i}'} for i in range(10)]

    with patch.object(create_scraper, 'fetch_page', return_value="<html></html>"):
        with patch.object(
                create_scraper, 'extract_content',
                return_value={'title': 'Test', 'content': '', 'url': '', 'images': []}):
            with patch('time.sleep'):
                pages = create_scraper.scrape_pages(page_links, max_pages=3)

    assert len(pages) == 3


def test_extract_guide_title_from_meta(create_scraper):
    """Test extracting guide title from meta tags."""
    html = """
    <html>
        <head>
            <meta name="product" content="AWS MSK" />
            <meta name="guide" content="Developer Guide" />
        </head>
    </html>
    """

    title = create_scraper.extract_guide_title(html)

    assert title == "AWS MSK Developer Guide"


def test_extract_guide_title_from_title_tag(create_scraper):
    """Test extracting guide title from title tag."""
    html = """
    <html>
        <head>
            <title>Page Name - AWS Lambda Guide</title>
        </head>
    </html>
    """

    title = create_scraper.extract_guide_title(html)

    assert title == "AWS Lambda Guide"


def test_extract_guide_title_fallback(create_scraper):
    """Test guide title extraction fallback."""
    html = "<html><head></head></html>"

    title = create_scraper.extract_guide_title(html)

    assert title == "AWS Documentation"


def test_remove_invalid_attributes(create_scraper):
    """Test removing invalid attributes from elements."""
    html = (
        '<div id="test" tab-id="1" data-toggle="modal" copy="true">'
        '<p id="para">Content</p>'
        '</div>'
    )
    soup = BeautifulSoup(html, 'lxml')
    main_content = soup.find('div')

    create_scraper._remove_invalid_attributes(  # pylint: disable=protected-access
        main_content)

    # After calling the method, invalid attributes should be removed from all elements
    # Check all elements in the tree
    assert main_content is not None
    for elem in main_content.find_all(True):
        assert not elem.has_attr(
            'tab-id'), f"Element {elem.name} still has tab-id"
        assert not elem.has_attr(
            'data-toggle'), f"Element {elem.name} still has data-toggle"
        assert not elem.has_attr('copy'), f"Element {elem.name} still has copy"
    # id attributes should be preserved for fragment link support
    div_elem = main_content
    assert div_elem.has_attr('id'), "div should still have id attribute"
    para_elem = main_content.find('p')
    assert para_elem.has_attr('id'), "p should still have id attribute"


def test_fix_links_with_non_string_href(create_scraper):
    """Test fixing links when href is not a string."""
    html = '<div><a href="">Link</a></div>'
    soup = BeautifulSoup(html, 'lxml')
    main_content = soup.find('div')
    base_url = "https://docs.aws.amazon.com/guide/page.html"

    # Should not raise exception
    create_scraper._fix_links_and_images(  # pylint: disable=protected-access
        main_content, base_url)


def test_extract_content_with_failed_fetch(create_scraper):
    """Test extract_content when main content is None."""
    html = "<html><body></body></html>"

    with patch.object(create_scraper, '_find_main_content', return_value=None):
        result = create_scraper.extract_content(html, "https://example.com")

    assert result is None


def test_scrape_pages_with_failed_extraction(create_scraper):
    """Test scraping when content extraction fails."""
    page_links = [
        {'url': 'https://example.com/1', 'title': 'Page 1'},
    ]

    with patch.object(create_scraper, 'fetch_page', return_value="<html></html>"):
        with patch.object(create_scraper, 'extract_content', return_value=None):
            with patch('time.sleep'):
                pages = create_scraper.scrape_pages(page_links)

    assert len(pages) == 0


def test_scrape_pages_with_failed_fetch(create_scraper):
    """Test scraping when page fetch fails."""
    page_links = [
        {'url': 'https://example.com/1', 'title': 'Page 1'},
    ]

    with patch.object(create_scraper, 'fetch_page', return_value=None):
        with patch('time.sleep'):
            pages = create_scraper.scrape_pages(page_links)

    assert len(pages) == 0


def test_fetch_page_connection_error(create_scraper):
    """Test page fetch with ConnectionError."""
    with patch.object(
            create_scraper.session, 'get', side_effect=ConnectionError("Connection failed")):
        with patch('time.sleep'):
            result = create_scraper.fetch_page("https://example.com")
            assert result is None


def test_fetch_page_timeout_error(create_scraper):
    """Test page fetch with TimeoutError."""
    with patch.object(create_scraper.session, 'get', side_effect=TimeoutError("Timeout")):
        with patch('time.sleep'):
            result = create_scraper.fetch_page("https://example.com")
            assert result is None


def test_extract_guide_title_no_meta_attributes(create_scraper):
    """Test extracting guide title when meta tags don't have get method."""
    html = """
    <html>
        <head>
            <meta name="product" />
            <meta name="guide" />
        </head>
    </html>
    """

    title = create_scraper.extract_guide_title(html)

    # Should fall back to default
    assert title == "AWS Documentation"


def test_extract_guide_title_only_title_tag(create_scraper):
    """Test guide title extraction with only title tag."""
    html = """
    <html>
        <head>
            <title>AWS Lambda Guide</title>
        </head>
    </html>
    """

    title = create_scraper.extract_guide_title(html)

    assert title == "AWS Lambda Guide"


def test_clean_content_removes_aws_specific_elements(create_scraper):
    """Test that AWS-specific custom elements are removed."""
    html = """
    <div>
        <p>Content to keep</p>
        <awsdocs-page-utilities>Utility content</awsdocs-page-utilities>
        <awsdocs-copyright>Copyright</awsdocs-copyright>
        <awsdocs-thumb-feedback>Feedback</awsdocs-thumb-feedback>
        <awsui-icon>Icon</awsui-icon>
        <div class="prev-next">Navigation</div>
        <div class="code-btn-container">Button</div>
        <div class="btn-copy-code">Copy</div>
        <div id="js_error_message">Error</div>
        <div id="doc-conventions">Conventions</div>
        <div id="main-col-footer">Footer</div>
    </div>
    """
    soup = BeautifulSoup(html, 'lxml')
    main_content = soup.find('div')

    create_scraper._clean_content(  # pylint: disable=protected-access
        main_content)

    # AWS-specific elements should be removed
    assert main_content is not None
    assert main_content.find('awsdocs-page-utilities') is None
    assert main_content.find('awsdocs-copyright') is None
    assert main_content.find('awsdocs-thumb-feedback') is None
    assert main_content.find('awsui-icon') is None

    # Class-based removals
    assert main_content.find('div', class_='prev-next') is None
    assert main_content.find('div', class_='code-btn-container') is None
    assert main_content.find('div', class_='btn-copy-code') is None

    # ID-based removals
    assert main_content.find('div', id='js_error_message') is None
    assert main_content.find('div', id='doc-conventions') is None
    assert main_content.find('div', id='main-col-footer') is None

    # Content should be preserved
    assert 'Content to keep' in str(main_content)


def test_remove_invalid_attributes_removes_all_attrs(create_scraper):
    """Test that all invalid attributes are properly removed."""
    html = """
    <div>
        <div id="test" tab-id="1" data-target="modal" data-toggle="collapse" copy="true">
            <p id="para" tab-id="2">Content</p>
            <span data-target="#menu">Link</span>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, 'lxml')
    main_content = soup.find('div')

    create_scraper._remove_invalid_attributes(  # pylint: disable=protected-access
        main_content)

    # Check all elements have invalid attributes removed

    assert main_content is not None
    for elem in main_content.find_all(True):
        assert not elem.has_attr(
            'tab-id'), f"Element {elem.name} still has tab-id"
        assert not elem.has_attr(
            'data-target'), f"Element {elem.name} still has data-target"
        assert not elem.has_attr(
            'data-toggle'), f"Element {elem.name} still has data-toggle"
        assert not elem.has_attr('copy'), f"Element {elem.name} still has copy"

    # id attributes should be preserved for fragment link support
    test_div = main_content.find('div', id='test')
    assert test_div is not None, "div with id='test' should exist"
    para = main_content.find('p', id='para')
    assert para is not None, "p with id='para' should exist"


def test_fetch_page_max_retries_exhausted(create_scraper):
    """Test that None is returned when max retries are exhausted."""
    # Simulate all retries failing
    with patch.object(
            create_scraper.session,
            'get',
            side_effect=[requests.RequestException("Error")] * 4
    ):
        with patch('time.sleep'):  # Don't actually sleep
            result = create_scraper.fetch_page("https://example.com")
            # Should return None after exhausting all retries
            assert result is None
