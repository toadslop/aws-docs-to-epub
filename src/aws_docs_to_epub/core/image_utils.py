"""Image handling utilities for cover generation and SVG conversion."""

import urllib.request
import io
import traceback
import gzip
from typing import Tuple, Optional, List, Union

from PIL import Image, ImageDraw, ImageFont
from cairosvg import svg2png
import requests


def fetch_image_from_url(url: str, session: requests.Session) -> Tuple[bytes, str]:
    """Fetch an image from a URL, handling SVG compression."""

    # Determine file extension
    url_lower = url.lower()
    if '.png' in url_lower:
        ext = 'png'
    elif '.jpg' in url_lower or '.jpeg' in url_lower:
        ext = 'jpg'
    elif '.svg' in url_lower:
        ext = 'svg'
    elif '.gif' in url_lower:
        ext = 'gif'
    elif '.webp' in url_lower:
        ext = 'webp'
    else:
        ext = 'png'

    # For SVG, use urllib to avoid encoding issues
    if ext == 'svg':
        req = urllib.request.Request(url)
        user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
        req.add_header(
            'User-Agent',
            user_agent
        )
        req.add_header('User-Agent', user_agent)
        req.add_header('Accept', 'image/svg+xml,image/*,*/*;q=0.8')
        req.add_header('Accept-Encoding', 'gzip, deflate')
        req.add_header('Referer', 'https://docs.aws.amazon.com/')

        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()

            # Check if it's gzip compressed
            if content[:2] == b'\x1f\x8b':
                print("Decompressing gzip-encoded SVG")
                content = gzip.decompress(content)

            return content, ext
    else:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.content, ext


def fetch_local_image(filepath: str) -> Tuple[bytes, str]:
    """Fetch an image from a local file."""
    url_lower = filepath.lower()
    if '.png' in url_lower:
        ext = 'png'
    elif '.jpg' in url_lower or '.jpeg' in url_lower:
        ext = 'jpg'
    elif '.svg' in url_lower:
        ext = 'svg'
    elif '.gif' in url_lower:
        ext = 'gif'
    elif '.webp' in url_lower:
        ext = 'webp'
    else:
        ext = 'png'

    with open(filepath, 'rb') as f:
        return f.read(), ext


def convert_svg_to_png(svg_data: bytes, target_width: int = 1280) -> Optional[Image.Image]:
    """Convert SVG data to PNG using cairosvg."""
    try:

        png_data = svg2png(bytestring=svg_data, output_width=target_width)
        if png_data:
            return Image.open(io.BytesIO(png_data))
    except ImportError:
        print("Warning: cairosvg not installed. Install with: pip install cairosvg")
    except (OSError, ValueError, RuntimeError) as e:
        print(f"Error converting SVG: {e}")

    return None


def _load_icon_image(icon_data: bytes, icon_ext: str) -> Image.Image:
    """Load and process icon image, handling SVG conversion."""
    if icon_ext.lower() == 'svg':
        print("Converting SVG to PNG...")
        print(f"SVG data starts with: {icon_data[:50]!r}")

        icon_img = convert_svg_to_png(icon_data, target_width=1280)
        if not icon_img:
            print("SVG conversion failed, using placeholder")
            icon_img = Image.new('RGBA', (1280, 1280), color='#E0E0E0')
            placeholder_draw = ImageDraw.Draw(icon_img)
            placeholder_draw.rectangle(
                ((100, 100), (1180, 1180)), outline='#999999', width=10)
    else:
        icon_img = Image.open(io.BytesIO(icon_data))

    if icon_img.mode != 'RGBA':
        icon_img = icon_img.convert('RGBA')

    return icon_img


def _resize_icon(icon_img: Image.Image, target_size: int = 1280) -> Image.Image:
    """Resize icon to target size while maintaining aspect ratio."""
    aspect_ratio = icon_img.width / icon_img.height

    if aspect_ratio > 1:
        new_width = target_size
        new_height = int(target_size / aspect_ratio)
    else:
        new_height = target_size
        new_width = int(target_size * aspect_ratio)

    return icon_img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def _load_font(size: int = 120) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    """Load a suitable font for the cover text."""
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("arial.ttf", size)
        except (OSError, IOError):
            return ImageFont.load_default()


def _calculate_optimal_font_and_text(
        text: str, draw: ImageDraw.ImageDraw, cover_width: int,
        cover_height: int, icon_height: int
) -> Tuple[Union[ImageFont.FreeTypeFont, ImageFont.ImageFont], List[str]]:
    """Calculate optimal font size and text layout to fit within cover dimensions.

    Args:
        text: Text to display
        draw: ImageDraw context for measurement
        cover_width: Width of cover
        cover_height: Height of cover
        icon_height: Height of icon (to calculate available space for text)

    Returns:
        Tuple of (font, lines)
    """
    # Calculate available space for text (leave margins and gap)
    margin = 100
    gap = 100
    available_width = cover_width - (2 * margin)
    available_height = cover_height - icon_height - gap - (2 * margin)

    # Try font sizes from 120 down to 60
    for font_size in range(120, 59, -10):
        font = _load_font(font_size)
        lines = _split_text_into_lines(text, font, draw, available_width)
        text_height = _calculate_text_height(lines, font, draw)

        # If it fits, return this font size
        if text_height <= available_height:
            return font, lines

    # If nothing fits, use smallest font
    font = _load_font(60)
    lines = _split_text_into_lines(text, font, draw, available_width)
    return font, lines


def _split_text_into_lines(text: str, font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont],
                           draw: ImageDraw.ImageDraw, max_width: int) -> List[str]:
    """Split text into lines that fit within max_width."""
    words = text.split()
    lines: List[str] = []
    current_line: List[str] = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))

    return lines


def _calculate_text_height(
    lines: List[str], font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont],
        draw: ImageDraw.ImageDraw, line_spacing: int = 20) -> int:
    """Calculate total height of text lines."""
    total_height = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_height = bbox[3] - bbox[1]
        total_height += text_height + line_spacing
    if total_height > 0:
        total_height -= line_spacing
    return int(total_height)


def _draw_text_lines(draw: ImageDraw.ImageDraw, lines: List[str],
                     font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont],
                     cover_width: int, start_y: int, *, line_spacing: int = 20) -> None:
    """Draw text lines centered on the cover."""
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (cover_width - text_width) // 2
        line_y = start_y + (i * (text_height + line_spacing))
        draw.text((text_x, line_y), line, fill='#232F3E', font=font)


def render_cover_image(service_name: str, icon_data: bytes, icon_ext: str,
                       cover_width: int = 1600, cover_height: int = 2400) -> Optional[bytes]:
    """
    Render a cover image as PNG with icon and service name.

    Args:
        service_name: The name to display on the cover
        icon_data: Raw bytes of the icon image
        icon_ext: File extension of the icon (svg, png, jpg, etc.)
        cover_width: Width of the cover image in pixels
        cover_height: Height of the cover image in pixels

    Returns:
        PNG image data as bytes
    """
    try:
        # Create cover and prepare components
        cover_img, draw = _create_cover_canvas(cover_width, cover_height)

        # Limit icon to 2/3 of cover dimensions
        max_icon_size = int(min(cover_width, cover_height) * 2 / 3)
        icon_img = _prepare_icon(icon_data, icon_ext, max_icon_size)

        # Calculate optimal font size and layout
        font, lines = _calculate_optimal_font_and_text(
            service_name, draw, cover_width, cover_height, icon_img.height)

        layout = _calculate_layout(
            icon_img, lines, font, draw, cover_width, cover_height)

        # Render cover
        _paste_icon(cover_img, icon_img, layout['icon_x'], layout['icon_y'])
        _draw_text_lines(draw, lines, font, cover_width, layout['text_y'])

        # Save to bytes
        return _save_image_to_bytes(cover_img)

    except (OSError, IOError, ValueError, RuntimeError) as e:
        print(f"Warning: Failed to render cover image: {e}")
        traceback.print_exc()
        return None


def _create_cover_canvas(width: int, height: int) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create a blank cover canvas with drawing context."""
    cover_img = Image.new('RGB', (width, height), color='#FFFFFF')
    draw = ImageDraw.Draw(cover_img)
    return cover_img, draw


def _prepare_icon(icon_data: bytes, icon_ext: str, max_size: int = 1280) -> Image.Image:
    """Load and resize icon image."""
    icon_img = _load_icon_image(icon_data, icon_ext)
    return _resize_icon(icon_img, target_size=max_size)


def _calculate_layout(icon_img: Image.Image, lines: List[str],
                      font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont],
                      draw: ImageDraw.ImageDraw, cover_width: int,
                      cover_height: int) -> dict:
    """Calculate positioning for icon and text."""
    total_text_height = _calculate_text_height(lines, font, draw)
    gap = 100
    total_height = icon_img.height + gap + total_text_height

    icon_y = int((cover_height - total_height) // 2)
    icon_x = int((cover_width - icon_img.width) // 2)
    text_y = icon_y + icon_img.height + gap

    return {'icon_x': icon_x, 'icon_y': icon_y, 'text_y': text_y}


def _paste_icon(cover_img: Image.Image, icon_img: Image.Image, x: int, y: int) -> None:
    """Paste icon onto cover with transparency support."""
    if icon_img.mode == 'RGBA':
        cover_img.paste(icon_img, (x, y), icon_img)
    else:
        cover_img.paste(icon_img, (x, y))


def _save_image_to_bytes(image: Image.Image) -> bytes:
    """Save PIL Image to PNG bytes."""
    output = io.BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    return output.read()
