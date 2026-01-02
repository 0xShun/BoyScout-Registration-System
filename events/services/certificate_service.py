"""
Certificate generation service for event attendance certificates.
Handles certificate image generation using PIL/Pillow.
"""
import os
from io import BytesIO
from datetime import datetime
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont


class CertificateService:
    """Service for generating event attendance certificates"""
    
    DEFAULT_FONT_PATHS = [
        '/System/Library/Fonts/Supplemental/Arial.ttf',  # macOS
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
        'C:\\Windows\\Fonts\\arial.ttf',  # Windows
        '/Library/Fonts/Arial.ttf',  # macOS alternative
    ]
    
    @staticmethod
    def generate_certificate(user, event, attendance):
        """
        Generate a certificate for a user's event attendance.
        
        Args:
            user: User object
            event: Event object
            attendance: Attendance object
            
        Returns:
            EventCertificate object
        """
        from events.models import EventCertificate
        
        # Check if certificate template exists
        if not hasattr(event, 'certificate_template'):
            raise ValueError(f"No certificate template found for event: {event.title}")
        
        template = event.certificate_template
        
        # Generate unique certificate number
        cert_number = EventCertificate.generate_certificate_number(event.id, user.id)
        
        # Create certificate image
        cert_image = CertificateService._create_certificate_image(
            template=template,
            participant_name=user.get_full_name(),
            event_name=event.title,
            event_date=event.date,
            cert_number=cert_number
        )
        
        # Save certificate to file
        image_io = BytesIO()
        cert_image.save(image_io, format='PNG', quality=95)
        image_file = ContentFile(image_io.getvalue(), name=f'certificate_{cert_number}.png')
        
        # Create EventCertificate record
        certificate = EventCertificate.objects.create(
            user=user,
            event=event,
            attendance=attendance,
            certificate_number=cert_number,
            certificate_file=image_file
        )
        
        return certificate
    
    @staticmethod
    def preview_certificate(template, preview_name="John Doe", preview_event="Sample Event"):
        """
        Generate a preview certificate with dummy data.
        
        Args:
            template: CertificateTemplate object
            preview_name: Sample participant name
            preview_event: Sample event name
            
        Returns:
            PIL Image object
        """
        preview_date = datetime(2025, 1, 15).date()
        preview_cert_number = "CERT-PREVIEW-12345"
        
        return CertificateService._create_certificate_image(
            template=template,
            participant_name=preview_name,
            event_name=preview_event,
            event_date=preview_date,
            cert_number=preview_cert_number
        )
    
    @staticmethod
    def _create_certificate_image(template, participant_name, event_name, event_date, cert_number):
        """
        Create certificate image by drawing text on template.
        
        Args:
            template: CertificateTemplate object
            participant_name: Full name of participant
            event_name: Name of the event
            event_date: Date object
            cert_number: Unique certificate number
            
        Returns:
            PIL Image object
        """
        # Open template image
        template_img = Image.open(template.template_image.path)
        
        # Convert to RGB if needed (for PNG with transparency)
        if template_img.mode != 'RGB':
            # Create white background
            background = Image.new('RGB', template_img.size, (255, 255, 255))
            if template_img.mode == 'RGBA':
                background.paste(template_img, mask=template_img.split()[3])  # Use alpha channel as mask
            else:
                background.paste(template_img)
            template_img = background
        
        # Create drawing context
        draw = ImageDraw.Draw(template_img)
        
        # Get font path
        font_path = CertificateService._get_font_path()
        
        try:
            # Draw participant name
            name_font = ImageFont.truetype(font_path, template.name_font_size)
            name_color = CertificateService._hex_to_rgb(template.name_color)
            CertificateService._draw_centered_text(
                draw, participant_name, template.name_x, template.name_y,
                name_font, name_color
            )
            
            # Draw event name
            event_font = ImageFont.truetype(font_path, template.event_font_size)
            event_color = CertificateService._hex_to_rgb(template.event_color)
            CertificateService._draw_centered_text(
                draw, event_name, template.event_name_x, template.event_name_y,
                event_font, event_color
            )
            
            # Draw date
            date_font = ImageFont.truetype(font_path, template.date_font_size)
            date_color = CertificateService._hex_to_rgb(template.date_color)
            date_str = event_date.strftime("%B %d, %Y")
            CertificateService._draw_centered_text(
                draw, date_str, template.date_x, template.date_y,
                date_font, date_color
            )
            
            # Draw certificate number
            cert_font = ImageFont.truetype(font_path, template.cert_number_font_size)
            cert_color = CertificateService._hex_to_rgb(template.cert_number_color)
            draw.text(
                (template.cert_number_x, template.cert_number_y),
                f"Certificate No: {cert_number}",
                font=cert_font,
                fill=cert_color
            )
            
        except Exception as e:
            # Fallback to default font if custom font fails
            print(f"Error loading custom font: {e}. Using default font.")
            # Draw with default font
            draw.text((template.name_x, template.name_y), participant_name, fill=(0, 0, 0))
            draw.text((template.event_name_x, template.event_name_y), event_name, fill=(0, 0, 0))
            draw.text((template.date_x, template.date_y), event_date.strftime("%B %d, %Y"), fill=(0, 0, 0))
            draw.text((template.cert_number_x, template.cert_number_y), f"Certificate No: {cert_number}", fill=(100, 100, 100))
        
        return template_img
    
    @staticmethod
    def _draw_centered_text(draw, text, x, y, font, color):
        """
        Draw text centered at given coordinates.
        
        Args:
            draw: ImageDraw object
            text: Text to draw
            x: X coordinate (center)
            y: Y coordinate (center)
            font: ImageFont object
            color: RGB tuple
        """
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calculate top-left position for centered text
        position = (x - text_width // 2, y - text_height // 2)
        
        # Draw text
        draw.text(position, text, font=font, fill=color)
    
    @staticmethod
    def _hex_to_rgb(hex_color):
        """
        Convert hex color to RGB tuple.
        
        Args:
            hex_color: Hex color string (e.g., "#FF0000")
            
        Returns:
            RGB tuple (e.g., (255, 0, 0))
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def _get_font_path():
        """
        Get path to a suitable TrueType font.
        
        Returns:
            Path to font file
        """
        # Try to find an available font
        for font_path in CertificateService.DEFAULT_FONT_PATHS:
            if os.path.exists(font_path):
                return font_path
        
        # If no font found, try to find any .ttf file in common locations
        search_paths = [
            '/System/Library/Fonts',
            '/Library/Fonts',
            '/usr/share/fonts',
            'C:\\Windows\\Fonts'
        ]
        
        for search_path in search_paths:
            if os.path.exists(search_path):
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        if file.endswith('.ttf'):
                            return os.path.join(root, file)
        
        # Fallback: return first path and let PIL handle the error
        return CertificateService.DEFAULT_FONT_PATHS[0]
