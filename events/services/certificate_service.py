"""
Certificate generation service for event certificates.

Handles creating certificate PNG images with auto-filled scout names, event details, and dates.
Uses Pillow for image manipulation.
"""

import logging
import os
from datetime import datetime
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from events.models import EventCertificate, CertificateTemplate, Attendance

logger = logging.getLogger(__name__)


def generate_certificate_number(event_id: int, user_id: int) -> str:
    """
    Generate a unique certificate number.

    Format: CERT-[EVENT_ID]-[USER_ID]-[TIMESTAMP]
    Example: CERT-23-145-20251120-133045

    Args:
        event_id: Event ID
        user_id: User ID

    Returns:
        Unique certificate number string
    """
    timestamp = timezone.now().strftime('%Y%m%d-%H%M%S')
    cert_number = f"CERT-{event_id}-{user_id}-{timestamp}"
    return cert_number


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color code to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., '#000000')

    Returns:
        Tuple of (R, G, B) values

    Raises:
        ValueError: If hex_color is not in valid format
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_font(font_size: int) -> ImageFont.FreeTypeFont:
    """
    Get a TrueType font for text rendering.

    Tries to use DejaVuSans.ttf (common on Linux/Mac), falls back to default.

    Args:
        font_size: Font size in pixels

    Returns:
        PIL ImageFont object
    """
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
        '/System/Library/Fonts/Arial.ttf',  # macOS
        'C:\\Windows\\Fonts\\arial.ttf',  # Windows
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except Exception as e:
                logger.warning(f"Failed to load font {font_path}: {e}")
                continue

    # Fallback to default font
    logger.warning("Using default font - text may not render as expected")
    return ImageFont.load_default()


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    position: Tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    max_width: Optional[int] = None
) -> None:
    """
    Draw text centered at the specified position.

    Args:
        draw: PIL ImageDraw object
        text: Text to draw
        position: (x, y) tuple for center position
        font: PIL ImageFont object
        fill: RGB color tuple
        max_width: Optional max width - will scale font if text exceeds it
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Scale down font if text exceeds max_width
    if max_width and text_width > max_width:
        scale_factor = max_width / text_width
        new_size = int(font.size * scale_factor * 0.9)  # 90% to have some padding
        font = get_font(new_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

    # Calculate top-left position to center the text
    x = position[0] - (text_width // 2)
    y = position[1] - (text_height // 2)

    draw.text((x, y), text, font=font, fill=fill)


@transaction.atomic
def generate_certificate(attendance: Attendance) -> Optional[EventCertificate]:
    """
    Generate a certificate PNG for an attendance record.

    This function:
    1. Gets the event's certificate template
    2. Loads the template image
    3. Overlays scout name, event name, date, and certificate number
    4. Saves the generated image
    5. Creates EventCertificate record in database

    Args:
        attendance: Attendance instance to create certificate for

    Returns:
        EventCertificate instance if successful, None if generation failed
    """
    try:
        event = attendance.event
        user = attendance.user

        # Get certificate template for this event
        try:
            template = CertificateTemplate.objects.get(event=event, is_active=True)
        except CertificateTemplate.DoesNotExist:
            logger.warning(f"No active certificate template for event {event.id}")
            return None

        # Load template image
        if not template.template_image:
            logger.warning(f"Certificate template {template.id} has no image")
            return None

        template_path = template.template_image.path
        if not os.path.exists(template_path):
            logger.error(f"Certificate template image not found: {template_path}")
            return None

        # Open template image
        base_image = Image.open(template_path).convert('RGB')
        draw = ImageDraw.Draw(base_image)

        # Prepare text data
        scout_name = user.get_full_name()
        event_name = event.title
        issue_date = timezone.now().strftime('%B %d, %Y')
        cert_number = generate_certificate_number(event.id, user.id)

        logger.info(f"Generating certificate for {scout_name} - Event: {event_name}")

        # Draw scout name
        try:
            name_font = get_font(template.name_font_size)
            name_color = hex_to_rgb(template.name_color)
            draw_centered_text(
                draw,
                scout_name,
                (template.name_x, template.name_y),
                name_font,
                name_color,
                max_width=int(base_image.width * 0.8)
            )
            logger.debug(f"Drew scout name at ({template.name_x}, {template.name_y})")
        except Exception as e:
            logger.error(f"Failed to draw scout name: {e}")
            raise

        # Draw event name
        try:
            event_font = get_font(template.event_font_size)
            event_color = hex_to_rgb(template.event_color)
            draw_centered_text(
                draw,
                event_name,
                (template.event_x, template.event_y),
                event_font,
                event_color,
                max_width=int(base_image.width * 0.8)
            )
            logger.debug(f"Drew event name at ({template.event_x}, {template.event_y})")
        except Exception as e:
            logger.error(f"Failed to draw event name: {e}")
            raise

        # Draw date
        try:
            date_font = get_font(template.date_font_size)
            date_color = hex_to_rgb(template.date_color)
            draw_centered_text(
                draw,
                issue_date,
                (template.date_x, template.date_y),
                date_font,
                date_color
            )
            logger.debug(f"Drew date at ({template.date_x}, {template.date_y})")
        except Exception as e:
            logger.error(f"Failed to draw date: {e}")
            raise

        # Draw certificate number (if configured)
        if (template.certificate_number_x and template.certificate_number_y):
            try:
                cert_num_font = get_font(template.certificate_number_font_size)
                cert_num_color = hex_to_rgb(template.certificate_number_color)
                draw_centered_text(
                    draw,
                    cert_number,
                    (template.certificate_number_x, template.certificate_number_y),
                    cert_num_font,
                    cert_num_color
                )
                logger.debug(f"Drew certificate number at ({template.certificate_number_x}, {template.certificate_number_y})")
            except Exception as e:
                logger.warning(f"Failed to draw certificate number: {e}")
                # Don't fail if cert number drawing fails - it's optional

        # Save generated image
        image_io = BytesIO()
        base_image.save(image_io, format='PNG', quality=95)
        image_io.seek(0)

        # Create EventCertificate record
        event_certificate = EventCertificate(
            event=event,
            user=user,
            certificate_template=template,
            certificate_number=cert_number
        )

        # Save image to ImageField
        filename = f"{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        event_certificate.certificate_image.save(
            filename,
            ContentFile(image_io.getvalue()),
            save=False
        )

        # Save to database
        event_certificate.save()
        logger.info(f"Certificate created successfully: {cert_number}")

        return event_certificate

    except Exception as e:
        logger.exception(f"Certificate generation failed for attendance {attendance.id}: {e}")
        # Return None instead of raising - we don't want to break attendance marking
        return None


def generate_certificate_image(template: 'CertificateTemplate', data: dict) -> Image.Image:
    """
    Generate a certificate image from template and data dictionary.
    Used for preview functionality without creating database records.

    Args:
        template: CertificateTemplate instance
        data: Dictionary containing:
            - scout_name: Student/scout full name
            - event_name: Event title
            - event_date: Event date (formatted string)
            - certificate_number: Certificate number

    Returns:
        PIL Image object

    Raises:
        Exception: If image generation fails
    """
    try:
        # Load base template image
        if not template.template_image:
            raise ValueError("Template image not found")

        base_image = Image.open(template.template_image.path).convert('RGBA')
        draw = ImageDraw.Draw(base_image)

        # Extract data
        scout_name = data.get('scout_name', 'N/A')
        event_name = data.get('event_name', 'N/A')
        event_date = data.get('event_date', 'N/A')
        cert_number = data.get('certificate_number', 'N/A')

        # Draw Event Name (center-top)
        event_font = get_font(template.event_font_size)
        event_color = hex_to_rgb(template.event_color)
        draw_centered_text(
            draw,
            event_name,
            (template.event_x, template.event_y),
            event_font,
            event_color,
            max_width=base_image.width - 100
        )

        # Draw Scout Name (center-middle)
        name_font = get_font(template.name_font_size)
        name_color = hex_to_rgb(template.name_color)
        draw_centered_text(
            draw,
            scout_name,
            (template.name_x, template.name_y),
            name_font,
            name_color,
            max_width=base_image.width - 100
        )

        # Draw Date (top-right) - right-aligned
        date_font = get_font(template.date_font_size)
        date_color = hex_to_rgb(template.date_color)
        bbox = draw.textbbox((0, 0), event_date, font=date_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            (template.date_x - text_width, template.date_y),
            event_date,
            font=date_font,
            fill=date_color
        )

        # Draw Certificate Number (top-left) - left-aligned
        cert_num_font = get_font(template.certificate_number_font_size)
        cert_num_color = hex_to_rgb(template.certificate_number_color)
        draw.text(
            (template.certificate_number_x, template.certificate_number_y),
            cert_number,
            font=cert_num_font,
            fill=cert_num_color
        )

        return base_image

    except Exception as e:
        logger.exception(f"Certificate image generation failed: {e}")
        raise
