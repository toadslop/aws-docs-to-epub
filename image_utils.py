"""Image handling utilities for cover generation and SVG conversion."""

import io
import os
import gzip
from PIL import Image, ImageDraw, ImageFont  # type: ignore


def fetch_image_from_url(url, session):
    """Fetch an image from a URL, handling SVG compression."""
    import urllib.request

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
        req.add_header(
            'User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
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


def fetch_local_image(filepath):
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


def convert_svg_to_png(svg_data, target_width=1280):
    """Convert SVG data to PNG using cairosvg."""
    try:
        from cairosvg import svg2png
        png_data = svg2png(bytestring=svg_data, output_width=target_width)
        if png_data:
            return Image.open(io.BytesIO(png_data))
    except ImportError:
        print("Warning: cairosvg not installed. Install with: pip install cairosvg")
    except Exception as e:
        print(f"Error converting SVG: {e}")

    return None


def render_cover_image(service_name, icon_data, icon_ext, cover_width=1600, cover_height=2400):
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
        # Create cover background
        cover_img = Image.new(
            'RGB', (cover_width, cover_height), color='#FFFFFF')
        draw = ImageDraw.Draw(cover_img)

        # Handle SVG conversion
        if icon_ext.lower() == 'svg':
            print("Converting SVG to PNG...")
            print(f"SVG data starts with: {icon_data[:50]}")

            icon_img = convert_svg_to_png(icon_data, target_width=1280)
            if not icon_img:
                print("SVG conversion failed, using placeholder")
                icon_img = Image.new('RGBA', (1280, 1280), color='#E0E0E0')
                placeholder_draw = ImageDraw.Draw(icon_img)
                placeholder_draw.rectangle(
                    [100, 100, 1180, 1180], outline='#999999', width=10)
        else:
            icon_img = Image.open(io.BytesIO(icon_data))

        # Convert to RGBA if needed
        if icon_img.mode != 'RGBA':
            icon_img = icon_img.convert('RGBA')

        # Resize icon to fill most of the width
        target_size = 1280
        aspect_ratio = icon_img.width / icon_img.height

        if aspect_ratio > 1:
            new_width = target_size
            new_height = int(target_size / aspect_ratio)
        else:
            new_height = target_size
            new_width = int(target_size * aspect_ratio)

        icon_img = icon_img.resize(
            (new_width, new_height), Image.Resampling.LANCZOS)

        # Load font
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("arial.ttf", 120)
            except (OSError, IOError):
                font = ImageFont.load_default()

        # Split text into lines
        words = service_name.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
            if text_width <= cover_width - 200:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))

        # Calculate total text height
        total_text_height = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_height = bbox[3] - bbox[1]
            total_text_height += text_height + 20
        if total_text_height > 0:
            total_text_height -= 20

        # Calculate total composition height and center vertically
        gap = 100
        total_height = icon_img.height + gap + total_text_height
        icon_y = (cover_height - total_height) // 2
        icon_x = (cover_width - icon_img.width) // 2

        # Paste icon
        if icon_img.mode == 'RGBA':
            cover_img.paste(icon_img, (icon_x, icon_y), icon_img)
        else:
            cover_img.paste(icon_img, (icon_x, icon_y))

        # Draw text
        text_y = icon_y + icon_img.height + gap
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (cover_width - text_width) // 2
            line_y = text_y + (i * (text_height + 20))
            draw.text((text_x, line_y), line, fill='#232F3E', font=font)

        # Save to bytes
        output = io.BytesIO()
        cover_img.save(output, format='PNG')
        output.seek(0)
        return output.read()

    except Exception as e:
        print(f"Warning: Failed to render cover image: {e}")
        import traceback
        traceback.print_exc()
        return None
