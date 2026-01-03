"""Comprehensive unit tests for image utils module."""
# pylint: disable=redefined-outer-name

from unittest.mock import Mock, patch, MagicMock, mock_open
from io import BytesIO
import gzip

import pytest
from PIL import Image, ImageDraw, ImageFont


from aws_docs_to_epub.core.image_utils import (
    fetch_image_from_url,
    fetch_local_image,
    convert_svg_to_png,
    render_cover_image,
    _load_icon_image,
    _resize_icon,
    _load_font,
    _split_text_into_lines,
    _calculate_text_height,
    _draw_text_lines
)


@pytest.fixture
def create_mock_session():
    """Create a mock requests session."""
    return Mock()


def test_fetch_image_from_url_png(create_mock_session):
    """Test fetching PNG image from URL."""
    mock_response = Mock()
    mock_response.content = b"fake png data"
    create_mock_session.get.return_value = mock_response

    data, ext = fetch_image_from_url(
        "https://example.com/image.png", create_mock_session)

    assert data == b"fake png data"
    assert ext == "png"


def test_fetch_image_from_url_jpg(create_mock_session):
    """Test fetching JPG image from URL."""
    mock_response = Mock()
    mock_response.content = b"fake jpg data"
    create_mock_session.get.return_value = mock_response

    _data, ext = fetch_image_from_url(
        "https://example.com/image.jpg", create_mock_session)

    assert ext == "jpg"


def test_fetch_image_from_url_svg(create_mock_session):
    """Test fetching SVG image from URL."""
    svg_data = b'<svg>test</svg>'

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.__enter__.return_value.read.return_value = svg_data
        mock_urlopen.return_value = mock_response

        data, ext = fetch_image_from_url(
            "https://example.com/image.svg", create_mock_session)

        assert ext == "svg"
        assert data == svg_data


def test_fetch_image_from_url_svg_gzipped(create_mock_session):
    """Test fetching gzipped SVG image from URL."""

    svg_data = b'<svg>test</svg>'
    gzipped_data = gzip.compress(svg_data)

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.__enter__.return_value.read.return_value = gzipped_data
        mock_urlopen.return_value = mock_response

        data, ext = fetch_image_from_url(
            "https://example.com/image.svg", create_mock_session)

        assert ext == "svg"
        assert data == svg_data


def test_fetch_local_image_png():
    """Test fetching local PNG image."""
    fake_data = b"fake png data"

    with patch('builtins.open', mock_open(read_data=fake_data)):
        data, ext = fetch_local_image('/path/to/image.png')

        assert data == fake_data
        assert ext == "png"


def test_fetch_local_image_svg():
    """Test fetching local SVG image."""
    fake_data = b"<svg>test</svg>"

    with patch('builtins.open', mock_open(read_data=fake_data)):
        data, ext = fetch_local_image('/path/to/image.svg')

        assert data == fake_data
        assert ext == "svg"


def test_convert_svg_to_png():
    """Test converting SVG to PNG."""
    svg_data = b'<svg><rect width="100" height="100"/></svg>'

    with patch('aws_docs_to_epub.core.image_utils.svg2png') as mock_svg2png:
        # Create a fake PNG image
        fake_png = BytesIO()
        img = Image.new('RGB', (100, 100), color='red')
        img.save(fake_png, format='PNG')
        fake_png.seek(0)

        mock_svg2png.return_value = fake_png.read()

        result = convert_svg_to_png(svg_data)

        assert result is not None
        assert isinstance(result, Image.Image)


def test_convert_svg_to_png_failure():
    """Test SVG conversion failure handling."""
    svg_data = b'<svg>test</svg>'

    with patch(
            'aws_docs_to_epub.core.image_utils.svg2png',
            side_effect=OSError("Conversion error")):
        result = convert_svg_to_png(svg_data)

        assert result is None


def test_convert_svg_to_png_import_error():
    """Test SVG conversion with ImportError."""
    svg_data = b'<svg>test</svg>'

    with patch('aws_docs_to_epub.core.image_utils.svg2png', side_effect=ImportError("No cairosvg")):
        result = convert_svg_to_png(svg_data)

        assert result is None


def test_load_icon_image_png():
    """Test loading PNG icon."""
    fake_png = BytesIO()
    img = Image.new('RGBA', (100, 100), color='red')
    img.save(fake_png, format='PNG')
    fake_png.seek(0)

    result = _load_icon_image(fake_png.read(), 'png')

    assert isinstance(result, Image.Image)
    assert result.mode == 'RGBA'


def test_load_icon_image_svg_success():
    """Test loading SVG icon with successful conversion."""
    svg_data = b'<svg>test</svg>'

    with patch('aws_docs_to_epub.core.image_utils.convert_svg_to_png') as mock_convert:
        mock_img = Image.new('RGBA', (100, 100))
        mock_convert.return_value = mock_img

        result = _load_icon_image(svg_data, 'svg')

        assert isinstance(result, Image.Image)


def test_load_icon_image_svg_failure():
    """Test loading SVG icon with failed conversion creates placeholder."""
    svg_data = b'<svg>test</svg>'

    with patch('aws_docs_to_epub.core.image_utils.convert_svg_to_png', return_value=None):
        result = _load_icon_image(svg_data, 'svg')

        assert isinstance(result, Image.Image)
        assert result.size == (1280, 1280)


def test_resize_icon_wide():
    """Test resizing wide icon."""
    img = Image.new('RGBA', (200, 100))

    result = _resize_icon(img, target_size=100)

    assert result.width == 100
    assert result.height == 50


def test_resize_icon_tall():
    """Test resizing tall icon."""
    img = Image.new('RGBA', (100, 200))

    result = _resize_icon(img, target_size=100)

    assert result.width == 50
    assert result.height == 100


def test_load_font_success():
    """Test loading font successfully."""
    with patch('aws_docs_to_epub.core.image_utils.ImageFont.truetype') as mock_truetype:
        mock_font = Mock()
        mock_truetype.return_value = mock_font

        result = _load_font()

        assert result == mock_font


def test_load_font_fallback():
    """Test loading font with fallback."""
    with patch(
            'aws_docs_to_epub.core.image_utils.ImageFont.truetype',
            side_effect=OSError("Font not found")):
        with patch('aws_docs_to_epub.core.image_utils.ImageFont.load_default') as mock_default:
            mock_font = Mock()
            mock_default.return_value = mock_font

            result = _load_font()

            assert result == mock_font


def test_split_text_into_lines():
    """Test splitting text into lines."""

    img = Image.new('RGB', (500, 500))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    text = "This is a very long text that should be split into multiple lines"
    lines = _split_text_into_lines(text, font, draw, 200)

    assert len(lines) > 1
    assert all(isinstance(line, str) for line in lines)


def test_calculate_text_height():
    """Test calculating text height."""

    img = Image.new('RGB', (500, 500))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    lines = ["Line 1", "Line 2", "Line 3"]
    height = _calculate_text_height(lines, font, draw)

    assert height > 0


def test_draw_text_lines():
    """Test drawing text lines."""

    img = Image.new('RGB', (500, 500))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    lines = ["Line 1", "Line 2"]
    _draw_text_lines(draw, lines, font, 500, 100)

    # If no exception, test passes


def test_render_cover_image_success():
    """Test rendering cover image successfully."""
    fake_png = BytesIO()
    img = Image.new('RGBA', (100, 100), color='red')
    img.save(fake_png, format='PNG')
    icon_data = fake_png.getvalue()

    result = render_cover_image(
        "AWS Test Service", icon_data, 'png', 800, 1200)

    assert result is not None
    assert isinstance(result, bytes)


def test_render_cover_image_with_svg():
    """Test rendering cover with SVG icon."""
    svg_data = b'<svg>test</svg>'

    with patch('aws_docs_to_epub.core.image_utils.convert_svg_to_png') as mock_convert:
        mock_img = Image.new('RGBA', (100, 100))
        mock_convert.return_value = mock_img

        result = render_cover_image("Test Service", svg_data, 'svg')

        assert result is not None


def test_render_cover_image_failure():
    """Test render cover image handles failures gracefully."""
    with patch('aws_docs_to_epub.core.image_utils._load_icon_image', side_effect=OSError("Error")):
        result = render_cover_image("Test", b"data", 'png')

        assert result is None


def test_fetch_image_default_extension(create_mock_session):
    """Test fetching image with unrecognized extension defaults to PNG."""
    mock_response = Mock()
    mock_response.content = b"fake data"
    create_mock_session.get.return_value = mock_response

    _data, ext = fetch_image_from_url(
        "https://example.com/image.unknown", create_mock_session)

    assert ext == "png"


def test_fetch_image_from_url_webp(create_mock_session):
    """Test fetching WebP image from URL."""
    mock_response = Mock()
    mock_response.content = b"fake webp data"
    create_mock_session.get.return_value = mock_response

    _data, ext = fetch_image_from_url(
        "https://example.com/image.webp", create_mock_session)

    assert ext == "webp"


def test_fetch_image_from_url_gif(create_mock_session):
    """Test fetching GIF image from URL."""
    mock_response = Mock()
    mock_response.content = b"fake gif data"
    create_mock_session.get.return_value = mock_response

    _data, ext = fetch_image_from_url(
        "https://example.com/image.gif", create_mock_session)

    assert ext == "gif"


def test_fetch_local_image_webp():
    """Test fetching local WebP image."""
    fake_data = b"fake webp data"

    with patch('builtins.open', mock_open(read_data=fake_data)):
        data, ext = fetch_local_image('/path/to/image.webp')

        assert data == fake_data
        assert ext == "webp"


def test_convert_svg_to_png_returns_none():
    """Test SVG conversion returns None on no data."""
    svg_data = b'<svg>test</svg>'

    with patch('aws_docs_to_epub.core.image_utils.svg2png', return_value=None):
        result = convert_svg_to_png(svg_data)

        assert result is None


def test_load_icon_image_converts_mode():
    """Test loading icon converts to RGBA if needed."""
    fake_png = BytesIO()
    img = Image.new('RGB', (100, 100), color='red')
    img.save(fake_png, format='PNG')
    fake_png.seek(0)

    result = _load_icon_image(fake_png.read(), 'png')

    assert result.mode == 'RGBA'


def test_fetch_image_from_url_jpeg_extension(create_mock_session):
    """Test fetching image with .jpeg extension."""
    mock_response = Mock()
    mock_response.content = b"fake jpeg data"
    create_mock_session.get.return_value = mock_response

    _data, ext = fetch_image_from_url(
        "https://example.com/image.jpeg", create_mock_session)

    assert ext == "jpg"


def test_fetch_local_image_jpeg():
    """Test fetching local JPEG image."""
    fake_data = b"fake jpeg data"

    with patch('builtins.open', mock_open(read_data=fake_data)):
        data, ext = fetch_local_image('/path/to/image.jpeg')

        assert data == fake_data
        assert ext == "jpg"


def test_fetch_local_image_gif():
    """Test fetching local GIF image."""
    fake_data = b"fake gif data"

    with patch('builtins.open', mock_open(read_data=fake_data)):
        data, ext = fetch_local_image('/path/to/image.gif')

        assert data == fake_data
        assert ext == "gif"


def test_fetch_local_image_default_extension():
    """Test fetching local image with unknown extension."""
    fake_data = b"fake data"

    with patch('builtins.open', mock_open(read_data=fake_data)):
        data, ext = fetch_local_image('/path/to/image.unknown')

        assert data == fake_data
        assert ext == "png"


def test_render_cover_image_exception_in_image_loading():
    """Test render cover handles exception in image loading."""
    with patch(
            'aws_docs_to_epub.core.image_utils._load_icon_image',
            side_effect=ValueError("Invalid image")):
        result = render_cover_image("Test", b"data", 'png')

        assert result is None
